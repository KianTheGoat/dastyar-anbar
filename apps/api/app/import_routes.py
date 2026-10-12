import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Account, ImportMapping, Workspace
from app.db.session import get_db
from app.importing import (
    FIELDS,
    STATUS_MAP,
    apply_preview,
    normalize,
    proposed_mapping,
    read_file,
    save_preview,
)
from app.security import account, csrf, rate_limit

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


async def uploaded(file: UploadFile, sheet: str):
    try:
        raw = await file.read(5 * 1024 * 1024 + 1)
        return read_file(raw, file.filename or "", sheet)
    finally:
        await file.close()


@router.post("/headers", dependencies=[Depends(csrf)])
async def headers(
    request: Request,
    kind: Literal["inventory", "sales", "aggregate"] = Form(),
    status_column: str = Form("", max_length=128),
    sheet: str = Form("", max_length=100),
    file: UploadFile = File(),
    owner: Account = Depends(account),
    db: Session = Depends(get_db),
):
    rate_limit(request, db, "import-headers", 30)
    names, rows = await uploaded(file, sheet)
    saved = db.get(ImportMapping, (owner.workspace_id, kind))
    mapping = proposed_mapping(names, kind, saved.mapping if saved else None)
    column = status_column or mapping.get("status")
    statuses = []
    if kind == "sales" and column in names:
        index = names.index(column)
        statuses = sorted(
            {
                str(row[index]).strip()
                for row in rows
                if index < len(row) and row[index] not in (None, "") and len(str(row[index])) <= 64
            }
        )[:50]
    return {
        "headers": names,
        "mapping": mapping,
        "fields": FIELDS[kind],
        "row_count": len(rows),
        "status_values": statuses,
        "status_mapping": {s: STATUS_MAP[s] for s in statuses if s in STATUS_MAP},
    }


@router.post("/preview", dependencies=[Depends(csrf)])
async def preview(
    request: Request,
    kind: Literal["inventory", "sales", "aggregate"] = Form(),
    mapping: str = Form(max_length=8192),
    status_mapping: str = Form("{}", max_length=8192),
    calendar: Literal["gregorian", "jalali"] = Form("gregorian"),
    timezone: Literal["UTC", "Asia/Tehran"] = Form("Asia/Tehran"),
    finalized: bool = Form(False),
    snapshot_at: datetime | None = Form(None),
    sheet: str = Form("", max_length=100),
    file: UploadFile = File(),
    owner: Account = Depends(account),
    db: Session = Depends(get_db),
):
    rate_limit(request, db, "import-preview", 30)
    names, values = await uploaded(file, sheet)
    try:
        mapping_data, statuses = json.loads(mapping), json.loads(status_mapping)
        if not isinstance(mapping_data, dict) or not isinstance(statuses, dict):
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(400, "invalid_mapping") from None
    rows, errors = normalize(
        names, values, kind, mapping_data, calendar, timezone, finalized, statuses
    )
    if errors:
        return {"errors": errors, "row_count": len(values)}
    workspace = db.get(Workspace, owner.workspace_id)
    return save_preview(
        db, workspace, request.app.state.settings, kind, rows, mapping_data, snapshot_at
    )


@router.post("/{batch_id}/apply", dependencies=[Depends(csrf)])
def apply(
    batch_id: UUID,
    request: Request,
    owner: Account = Depends(account),
    db: Session = Depends(get_db),
):
    rate_limit(request, db, "import-apply", 30)
    return apply_preview(db, owner.workspace_id, batch_id, request.app.state.settings)


@router.get("")
def history(owner: Account = Depends(account), db: Session = Depends(get_db)):
    from app.db.models import ImportBatch

    return [
        {
            "kind": b.kind,
            "row_count": b.row_count,
            "applied": b.applied,
            "created_at": b.created_at.isoformat(),
        }
        for b in db.scalars(
            select(ImportBatch)
            .where(ImportBatch.workspace_id == owner.workspace_id)
            .order_by(ImportBatch.created_at.desc())
            .limit(20)
        )
    ]
