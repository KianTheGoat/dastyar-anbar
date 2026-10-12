import json
import re
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials
from pydantic import BaseModel, ConfigDict, Field, StrictStr
from requests import RequestException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Account, ImportBatch, SheetConnection, Variant
from app.db.session import get_db
from app.importing import clean_headers, normalize, proposed_mapping, save_preview
from app.security import account, audit, csrf, decrypt, encrypt, lock_workspace, rate_limit, utcnow

router = APIRouter(prefix="/api/v1/sheets", tags=["sheets"])


class ConnectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spreadsheet_id: StrictStr = Field(pattern=r"^[a-zA-Z0-9_-]{20,100}$")
    inventory_range: StrictStr = Field(pattern=r"^[\w '\-\u0600-\u06ff]{1,80}!A1:[A-Z]{1,2}10001$")
    sales_range: StrictStr = Field(pattern=r"^[\w '\-\u0600-\u06ff]{1,80}!A1:[A-Z]{1,2}10001$")
    sales_kind: Literal["sales", "aggregate"] = "sales"
    calendar: Literal["gregorian", "jalali"] = "gregorian"
    timezone: Literal["UTC", "Asia/Tehran"] = "Asia/Tehran"
    finalized: bool = False
    inventory_mapping: dict[str, str] = Field(default_factory=dict, max_length=10)
    sales_mapping: dict[str, str] = Field(default_factory=dict, max_length=10)
    status_mapping: dict[str, str] = Field(default_factory=dict, max_length=50)


def credentials_for(settings, workspace_id) -> Credentials | None:
    if not settings.google_credentials_dir:
        return None
    root = Path(settings.google_credentials_dir).resolve()
    filename = root / (str(workspace_id) + ".json")
    if not filename.is_file() or filename.is_symlink() or filename.resolve().parent != root:
        return None
    try:
        info = json.loads(filename.read_text(encoding="utf-8"))
        if (
            info.get("type") != "service_account"
            or info.get("token_uri") != "https://oauth2.googleapis.com/token"
        ):
            raise ValueError()
        return Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
    except (OSError, ValueError, KeyError):
        raise HTTPException(503, "sheet_credentials_invalid") from None


@router.get("/connection")
def connection(request: Request, owner: Account = Depends(account), db: Session = Depends(get_db)):
    credentials = credentials_for(request.app.state.settings, owner.workspace_id)
    stored = db.get(SheetConnection, owner.workspace_id)
    return {
        "configured": credentials is not None,
        "service_account_email": credentials.service_account_email if credentials else None,
        "connection": decrypt(request.app.state.settings, stored.payload) if stored else None,
        "last_synced_at": stored.last_synced_at.isoformat()
        if stored and stored.last_synced_at
        else None,
        "scope": "خواندن شیت‌هایی که با حساب اختصاصی فروشگاه به اشتراک می‌گذارید",
    }


@router.post("/connect", dependencies=[Depends(csrf)])
def connect(
    body: ConnectionInput,
    request: Request,
    owner: Account = Depends(account),
    db: Session = Depends(get_db),
):
    rate_limit(request, db, "sheet-connect", 10)
    if not credentials_for(request.app.state.settings, owner.workspace_id):
        raise HTTPException(503, "sheet_not_provisioned")
    for value in [body.inventory_range, body.sales_range]:
        column = re.search(r":([A-Z]+)10001$", value).group(1)
        number = sum((ord(c) - 64) * 26**i for i, c in enumerate(reversed(column)))
        if number > 64:
            raise HTTPException(400, "sheet_column_limit")
    lock_workspace(db, owner.workspace_id)
    stored = db.get(SheetConnection, owner.workspace_id)
    if not stored:
        stored = SheetConnection(workspace_id=owner.workspace_id, payload="")
        db.add(stored)
    stored.payload = encrypt(request.app.state.settings, body.model_dump())
    stored.last_synced_at = None
    db.execute(
        delete(ImportBatch).where(
            ImportBatch.workspace_id == owner.workspace_id,
            ImportBatch.kind == "bundle",
            ImportBatch.applied.is_(False),
        )
    )
    audit(db, owner.workspace_id, "sheet_connected")
    db.commit()
    return {"ok": True}


def fetch_values(credentials, config: dict) -> list[list[list]]:
    try:
        with AuthorizedSession(credentials) as session:
            response = session.get(
                f"https://sheets.googleapis.com/v4/spreadsheets/{config['spreadsheet_id']}/values:batchGet",
                params={
                    "ranges": [config["inventory_range"], config["sales_range"]],
                    "valueRenderOption": "FORMULA",
                    "dateTimeRenderOption": "FORMATTED_STRING",
                },
                timeout=(5, 20),
                stream=True,
            )
            if response.status_code != 200:
                raise HTTPException(502, "sheet_access_failed")
            raw = bytearray()
            for part in response.iter_content(65536):
                raw.extend(part)
                if len(raw) > 5 * 1024 * 1024:
                    raise HTTPException(413, "sheet_too_large")
            values = json.loads(raw)["valueRanges"]
            return [v.get("values", []) for v in values]
    except (RequestException, GoogleAuthError, ValueError, KeyError):
        raise HTTPException(502, "sheet_access_failed") from None


@router.post("/sync", dependencies=[Depends(csrf)])
def sync(request: Request, owner: Account = Depends(account), db: Session = Depends(get_db)):
    rate_limit(request, db, "sheet-sync", 10)
    settings = request.app.state.settings
    stored = db.get(SheetConnection, owner.workspace_id)
    credentials = credentials_for(settings, owner.workspace_id)
    if not stored or not credentials:
        raise HTTPException(400, "sheet_not_connected")
    config = decrypt(settings, stored.payload)
    db.rollback()  # Do not hold a transaction while waiting for Google.
    values = fetch_values(credentials, config)
    if len(values) != 2:
        raise HTTPException(400, "invalid_sheet")
    result, maps = {}, {}
    for kind, table, explicit in [
        ("inventory", values[0], config["inventory_mapping"]),
        (config["sales_kind"], values[1], config["sales_mapping"]),
    ]:
        names, data = clean_headers(table)
        mapping = explicit or proposed_mapping(names, kind)
        rows, errors = normalize(
            names,
            data,
            kind,
            mapping,
            config["calendar"],
            config["timezone"],
            config["finalized"],
            config["status_mapping"],
        )
        if errors:
            return {"errors": errors, "kind": kind}
        result[kind], maps[kind] = rows, mapping
    workspace = lock_workspace(db, owner.workspace_id)
    # Check again after network I/O; disconnect/reconnect invalidates this fetch.
    current = db.get(SheetConnection, owner.workspace_id, populate_existing=True)
    if not current or decrypt(settings, current.payload) != config:
        raise HTTPException(409, "sheet_connection_changed")
    known = set(db.scalars(select(Variant.sku).where(Variant.workspace_id == owner.workspace_id)))
    known |= {r["sku"] for r in result["inventory"]}
    if any(r["sku"] not in known for r in result[config["sales_kind"]]):
        raise HTTPException(400, "unknown_sku")
    now = utcnow()
    preview = save_preview(
        db,
        workspace,
        settings,
        "inventory",
        result["inventory"],
        maps["inventory"],
        now,
        commit=False,
    )
    batch = db.get(ImportBatch, UUID(preview["id"]))
    batch.kind = "bundle"
    batch.row_count += len(result[config["sales_kind"]])
    batch.payload = encrypt(
        settings,
        {
            "inventory": result["inventory"],
            "sales": result[config["sales_kind"]],
            "sales_kind": config["sales_kind"],
            "maps": maps,
            "snapshot_at": now.isoformat(),
        },
    )
    db.commit()
    return preview | {
        "kind": "bundle",
        "row_count": batch.row_count,
        "inventory_rows": len(result["inventory"]),
        "sales_rows": len(result[config["sales_kind"]]),
    }


@router.delete("/connection", dependencies=[Depends(csrf)])
def disconnect(owner: Account = Depends(account), db: Session = Depends(get_db)):
    lock_workspace(db, owner.workspace_id)
    db.execute(delete(SheetConnection).where(SheetConnection.workspace_id == owner.workspace_id))
    db.execute(
        delete(ImportBatch).where(
            ImportBatch.workspace_id == owner.workspace_id,
            ImportBatch.kind == "bundle",
            ImportBatch.applied.is_(False),
        )
    )
    audit(db, owner.workspace_id, "sheet_disconnected")
    db.commit()
    return {"ok": True}
