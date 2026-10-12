import csv
import io
import json
from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr
from sqlalchemy import case, func, select, text
from sqlalchemy.orm import Session

from app.db.models import (
    Account,
    AggregateSale,
    AuditEvent,
    Category,
    DeletionMarker,
    ImportBatch,
    ImportMapping,
    SaleLine,
    SheetConnection,
    Variant,
    Workspace,
)
from app.db.session import get_db
from app.domain.inventory import Thresholds, classify
from app.importing import csv_cell
from app.security import (
    account,
    audit,
    csrf,
    decrypt,
    digest,
    lock_workspace,
    rate_limit,
    utcnow,
    verify_password,
)

router = APIRouter(prefix="/api/v1", tags=["warehouse"])


def report(
    db: Session,
    workspace_id,
    start: date | None = None,
    end: date | None = None,
    category_id: UUID | None = None,
) -> dict:
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(404, "not_found")
    today = utcnow().astimezone(ZoneInfo("Asia/Tehran")).date()
    end = end or today
    start = start or end - timedelta(days=29)
    if start > end or (end - start).days > 366:
        raise HTTPException(400, "invalid_period")
    if category_id and not db.scalar(
        select(Category.id).where(Category.id == category_id, Category.workspace_id == workspace_id)
    ):
        raise HTTPException(404, "not_found")
    if workspace.sales_mode == "aggregate":
        start, end = workspace.aggregate_start, workspace.aggregate_end
        totals = (
            select(AggregateSale.variant_id.label("id"), AggregateSale.net_units.label("units"))
            .where(AggregateSale.workspace_id == workspace_id)
            .subquery()
        )
    else:
        zone = ZoneInfo("Asia/Tehran")
        from_time = datetime.combine(start, datetime.min.time(), zone)
        until_time = datetime.combine(end + timedelta(days=1), datetime.min.time(), zone)
        units = case(
            (
                SaleLine.status.in_(["preparing", "shipping", "completed"]),
                SaleLine.quantity - SaleLine.returned_quantity,
            ),
            else_=0,
        )
        totals = (
            select(SaleLine.variant_id.label("id"), func.sum(units).label("units"))
            .where(
                SaleLine.workspace_id == workspace_id,
                SaleLine.sold_at >= from_time,
                SaleLine.sold_at < until_time,
            )
            .group_by(SaleLine.variant_id)
            .subquery()
        )
    statement = (
        select(Variant, Category, func.coalesce(totals.c.units, 0))
        .join(
            Category,
            (Category.id == Variant.category_id) & (Category.workspace_id == Variant.workspace_id),
        )
        .outerjoin(totals, totals.c.id == Variant.id)
        .where(Variant.workspace_id == workspace_id)
    )
    if category_id:
        statement = statement.where(Variant.category_id == category_id)
    rows, counts = [], {"low": 0, "normal": 0, "high": 0}
    updated = None
    stale_before = utcnow() - timedelta(hours=24)
    for variant, category, sold in db.execute(statement):
        state = classify(variant.available, Thresholds(category.low_max, category.high_min)).value
        counts[state] += 1
        updated = (
            max(updated, variant.inventory_updated_at) if updated else variant.inventory_updated_at
        )
        rows.append(
            {
                "id": str(variant.id),
                "sku": variant.sku,
                "name": variant.name,
                "color": variant.color,
                "size": variant.size,
                "category": category.name,
                "category_id": str(category.id),
                "available": variant.available,
                "net_units": int(sold),
                "state": state,
                "low_max": category.low_max,
                "high_min": category.high_min,
                "replenishment": variant.replenishment,
                "needs_review": state == "low" and sold == 0,
                "priority": None,
                "updated_at": variant.inventory_updated_at.isoformat(),
                "stale": variant.inventory_updated_at < stale_before,
            }
        )
    candidates = sorted(
        [
            r
            for r in rows
            if r["state"] == "low" and r["net_units"] > 0 and r["replenishment"] != "producing"
        ],
        key=lambda r: (-r["net_units"], r["available"], r["sku"]),
    )
    for rank, item in enumerate(candidates, 1):
        item["priority"] = rank
    rows.sort(key=lambda r: (r["priority"] is None, r["priority"] or 0, -r["net_units"], r["sku"]))
    return {
        "rows": rows,
        "counts": counts,
        "priorities": len(candidates),
        "stale_count": sum(r["stale"] for r in rows),
        "sales_mode": workspace.sales_mode,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "data_updated_at": updated.isoformat() if updated else None,
        "generated_at": utcnow().isoformat(),
        "revision": workspace.data_revision,
    }


@router.get("/dashboard")
def dashboard(
    start: date | None = None,
    end: date | None = None,
    category_id: UUID | None = None,
    owner: Account = Depends(account),
    db: Session = Depends(get_db),
):
    data = report(db, owner.workspace_id, start, end, category_id)
    return {k: v for k, v in data.items() if k != "rows"}


@router.get("/variants")
def variants(
    start: date | None = None,
    end: date | None = None,
    category_id: UUID | None = None,
    state: Literal["low", "normal", "high"] | None = None,
    search: str = Query("", max_length=100),
    page: int = Query(1, ge=1, le=200),
    limit: int = Query(50, ge=1, le=100),
    priority_only: bool = False,
    owner: Account = Depends(account),
    db: Session = Depends(get_db),
):
    data = report(db, owner.workspace_id, start, end, category_id)
    rows = data.pop("rows")
    if state:
        rows = [r for r in rows if r["state"] == state]
    if search:
        rows = [
            r
            for r in rows
            if search.casefold()
            in " ".join(str(r[k]) for k in ["sku", "name", "color", "size"]).casefold()
        ]
    if priority_only:
        rows = [r for r in rows if r["priority"] is not None]
    return data | {
        "rows": rows[(page - 1) * limit : page * limit],
        "total": len(rows),
        "page": page,
    }


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    low_max: StrictInt = Field(ge=0, le=1_000_000)
    high_min: StrictInt = Field(ge=1, le=1_000_000)


@router.get("/categories")
def categories(owner: Account = Depends(account), db: Session = Depends(get_db)):
    return [
        {"id": str(c.id), "name": c.name, "low_max": c.low_max, "high_min": c.high_min}
        for c in db.scalars(
            select(Category)
            .where(Category.workspace_id == owner.workspace_id)
            .order_by(Category.name)
        )
    ]


@router.patch("/categories/{category_id}", dependencies=[Depends(csrf)])
def update_category(
    category_id: UUID,
    body: CategoryUpdate,
    owner: Account = Depends(account),
    db: Session = Depends(get_db),
):
    try:
        Thresholds(body.low_max, body.high_min)
    except ValueError:
        raise HTTPException(400, "invalid_thresholds") from None
    workspace = lock_workspace(db, owner.workspace_id)
    row = db.scalar(
        select(Category).where(
            Category.id == category_id, Category.workspace_id == owner.workspace_id
        )
    )
    if not row:
        raise HTTPException(404, "not_found")
    row.low_max, row.high_min = body.low_max, body.high_min
    workspace.data_revision += 1
    audit(db, owner.workspace_id, "category_thresholds_changed")
    db.commit()
    return {"ok": True}


class ReplenishmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["none", "planned", "producing"]


@router.patch("/variants/{variant_id}/replenishment", dependencies=[Depends(csrf)])
def replenish(
    variant_id: UUID,
    body: ReplenishmentInput,
    owner: Account = Depends(account),
    db: Session = Depends(get_db),
):
    workspace = lock_workspace(db, owner.workspace_id)
    row = db.scalar(
        select(Variant).where(Variant.id == variant_id, Variant.workspace_id == owner.workspace_id)
    )
    if not row:
        raise HTTPException(404, "not_found")
    row.replenishment = body.state
    workspace.data_revision += 1
    audit(db, owner.workspace_id, "replenishment_changed")
    db.commit()
    return {"ok": True}


@router.get("/export.csv")
def export_csv(
    request: Request,
    start: date | None = None,
    end: date | None = None,
    owner: Account = Depends(account),
    db: Session = Depends(get_db),
):
    rate_limit(request, db, "export", 30)
    data = report(db, owner.workspace_id, start, end)
    output = io.StringIO()
    writer = csv.writer(output)
    fields = [
        "sku",
        "name",
        "category",
        "color",
        "size",
        "available",
        "net_units",
        "state",
        "priority",
        "replenishment",
    ]
    writer.writerow(fields + ["period_start", "period_end", "sales_mode"])
    for row in data["rows"]:
        writer.writerow(
            [csv_cell(row.get(f) if row.get(f) is not None else "") for f in fields]
            + [data["period_start"], data["period_end"], data["sales_mode"]]
        )
    audit(db, owner.workspace_id, "csv_export", len(data["rows"]))
    db.commit()
    return Response(
        "\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="inventory-report.csv"'},
    )


@router.get("/assistant")
def assistant(
    topic: Literal["priorities", "excess", "review", "explain"] = "priorities",
    start: date | None = None,
    end: date | None = None,
    owner: Account = Depends(account),
    db: Session = Depends(get_db),
):
    data = report(db, owner.workspace_id, start, end)
    rows = data["rows"]
    if topic == "explain":
        message = (
            "کالاهای کم‌موجودی بر اساس فروش خالص بیشتر، سپس موجودی کمتر مرتب می‌شوند. "
            "کالاهای در حال تولید دوباره در صف پیشنهاد قرار نمی‌گیرند."
        )
        selected = []
    else:
        selected = [
            r
            for r in rows
            if (
                r["priority"] is not None
                if topic == "priorities"
                else r["state"] == "high"
                if topic == "excess"
                else r["needs_review"]
            )
        ][:5]
        message = (
            "برای این پرسش موردی پیدا نشد."
            if not selected
            else {
                "priorities": "این رنگ و سایزها در اولویت تأمین هستند.",
                "excess": "این موارد از حد موجودی زیاد دسته‌بندی عبور کرده‌اند.",
                "review": (
                    "این موارد کمبود دارند، اما در بازهٔ گزارش فروش ثبت‌شده ندارند؛ "
                    "پیش از تولید بررسی‌شان کنید."
                ),
            }[topic]
        )
    return {
        "message": message,
        "items": selected,
        "period_start": data["period_start"],
        "period_end": data["period_end"],
        "data_updated_at": data["data_updated_at"],
    }


@router.get("/activity")
def activity(owner: Account = Depends(account), db: Session = Depends(get_db)):
    return [
        {"action": r.action, "row_count": r.row_count, "created_at": r.created_at.isoformat()}
        for r in db.scalars(
            select(AuditEvent)
            .where(AuditEvent.workspace_id == owner.workspace_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(30)
        )
    ]


@router.get("/account/export")
def export_account(
    request: Request, owner: Account = Depends(account), db: Session = Depends(get_db)
):
    rate_limit(request, db, "account-export", 5)
    workspace_id, email = owner.workspace_id, owner.email
    factory = request.app.state.db_factory
    audit(db, workspace_id, "account_export")
    db.commit()

    def stream():
        with factory() as session:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            workspace = session.get(Workspace, workspace_id)
            if not workspace:
                yield "{}"
                return
            yield json.dumps(
                {
                    "account": {
                        "email": email,
                        "policy_version": owner.policy_version,
                        "created_at": owner.created_at.isoformat(),
                        "verified": owner.verified,
                    },
                    "workspace": {
                        "name": workspace.name,
                        "sales_mode": workspace.sales_mode,
                        "aggregate_start": str(workspace.aggregate_start)
                        if workspace.aggregate_start
                        else None,
                        "aggregate_end": str(workspace.aggregate_end)
                        if workspace.aggregate_end
                        else None,
                    },
                },
                ensure_ascii=False,
            )[:-1]
            for label, model in [
                ("categories", Category),
                ("variants", Variant),
                ("sales", SaleLine),
                ("aggregate_sales", AggregateSale),
                ("column_mappings", ImportMapping),
                ("import_history", ImportBatch),
                ("activity", AuditEvent),
            ]:
                yield ',"' + label + '":['
                first = True
                for row in session.scalars(
                    select(model)
                    .where(model.workspace_id == workspace_id)
                    .execution_options(yield_per=500)
                ):
                    if not first:
                        yield ","
                    first = False
                    yield json.dumps(
                        {
                            c.name: getattr(row, c.name)
                            for c in model.__table__.columns
                            if c.name != "payload"
                        },
                        default=str,
                        ensure_ascii=False,
                    )
                yield "]"
            connection = session.get(SheetConnection, workspace_id)
            yield ',"sheet_connection":' + json.dumps(
                decrypt(request.app.state.settings, connection.payload) if connection else None,
                ensure_ascii=False,
            )
            yield "}"

    return StreamingResponse(
        stream(),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="workspace-data.json"'},
    )


class DeleteAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: StrictStr = Field(max_length=128)
    confirmation: StrictStr


@router.delete("/account", dependencies=[Depends(csrf)])
def delete_account(
    body: DeleteAccount,
    request: Request,
    response: Response,
    owner: Account = Depends(account),
    db: Session = Depends(get_db),
):
    rate_limit(request, db, "delete-account", 5)
    if body.confirmation != "حذف حساب" or not verify_password(owner.password_hash, body.password):
        raise HTTPException(400, "deletion_confirmation_invalid")
    workspace = lock_workspace(db, owner.workspace_id)
    db.delete(workspace)
    db.add(
        DeletionMarker(
            workspace_hash=digest(str(workspace.id)),
            expires_at=utcnow()
            + timedelta(days=request.app.state.settings.backup_retention_days + 1),
        )
    )
    db.commit()
    response.delete_cookie(
        request.app.state.settings.cookie_name,
        path="/",
        secure=request.app.state.settings.app_env == "production",
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}
