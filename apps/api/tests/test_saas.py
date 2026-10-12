import io
import json
import os
import secrets
from datetime import timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.orm import sessionmaker
from test_database import DATABASE_URL

from app import auth, importing, sheets
from app.backups import backup, expire_backups, restore
from app.config import POLICY_VERSION, Settings
from app.db.models import Account, BrowserSession, DeletionMarker, ImportBatch, RateBucket, Variant
from app.main import create_app
from app.maintenance import cleanup
from app.security import digest, utcnow

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="Dedicated PostgreSQL test DB required")
ORIGIN = "http://127.0.0.1:5173"
PASSWORD = "synthetic-long-password-42"


@pytest.fixture
def clients(monkeypatch):
    engine = create_engine(DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE workspaces CASCADE"))
        connection.execute(delete(RateBucket))
        connection.execute(delete(DeletionMarker))
    factory = sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        app_env="test",
        allowed_hosts="testserver",
        database_url=DATABASE_URL,
        app_secret=secrets.token_hex(32),
        smtp_host="smtp.invalid",
        smtp_from="test@example.com",
    )
    sent = []
    monkeypatch.setattr(
        auth,
        "send_token_email",
        lambda settings, recipient, token, purpose: sent.append((recipient, token, purpose)),
    )
    app = create_app(settings)
    a, b = TestClient(app), TestClient(app)
    yield a, b, factory, settings, sent
    a.close()
    b.close()
    app.state.db_factory.kw["bind"].dispose()
    engine.dispose()


def bootstrap(client):
    result = client.get("/api/v1/auth/session")
    assert result.status_code == 200, result.text
    return {"Origin": ORIGIN, "X-CSRF-Token": result.json()["csrf_token"]}


def register(client, name="a"):
    headers = bootstrap(client)
    response = client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={
            "email": f"{name}@example.com",
            "password": PASSWORD,
            "workspace_name": name,
            "accepted_policy": True,
            "policy_version": POLICY_VERSION,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["account"]["email"] == f"{name}@example.com"
    return bootstrap(client)


def preview(client, headers, kind, data, mapping=None, **options):
    fields = {
        "inventory": ["sku", "name", "category", "color", "size", "available"],
        "sales": [
            "source",
            "order_id",
            "line_id",
            "sku",
            "sold_at",
            "quantity",
            "status",
            "returned_quantity",
        ],
        "aggregate": ["sku", "net_units", "period_start", "period_end"],
    }[kind]
    form = {"kind": kind, "mapping": json.dumps(mapping or {f: f for f in fields}), **options}
    response = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data=form,
        files={"file": ("synthetic.csv", data.encode(), "text/csv")},
    )
    return response


def import_inventory(client, headers, sku="001", quantity=2):
    result = preview(
        client,
        headers,
        "inventory",
        f"sku,name,category,color,size,available\n{sku},Synthetic shoe,Shoes,black,42,{quantity}\n",
    )
    assert result.status_code == 200, result.text
    batch = result.json()["id"]
    response = client.post(f"/api/v1/imports/{batch}/apply", headers=headers)
    assert response.status_code == 200, response.text
    return batch


def test_auth_csrf_rotation_logout_and_private_response(clients):
    a, _, factory, _, _ = clients
    headers = bootstrap(a)
    old_cookie = a.cookies.get("anbar_session_dev")
    body = {
        "email": "a@example.com",
        "password": PASSWORD,
        "workspace_name": "A",
        "accepted_policy": True,
        "policy_version": POLICY_VERSION,
    }
    assert a.post("/api/v1/auth/register", json=body).status_code == 403
    assert (
        a.post(
            "/api/v1/auth/register", headers=headers | {"Origin": "https://evil.invalid"}, json=body
        ).status_code
        == 403
    )
    assert a.post("/api/v1/auth/register", headers=headers, json=body).status_code == 200
    assert a.cookies.get("anbar_session_dev") != old_cookie
    with factory() as db:
        assert db.get(BrowserSession, digest(old_cookie)) is None
        owner = db.scalar(select(Account))
        assert owner.password_hash.startswith("$argon2id$") and PASSWORD not in owner.password_hash
    assert a.get("/api/v1/variants").status_code == 200
    assert a.post("/api/v1/auth/logout", headers=bootstrap(a)).status_code == 200
    assert a.get("/api/v1/variants").status_code == 401
    response = a.post(
        "/api/v1/auth/login", headers=bootstrap(a), json={"email": "invalid", "password": PASSWORD}
    )
    assert response.status_code == 422 and PASSWORD not in response.text


def test_import_replay_status_transition_returns_and_ranking(clients):
    a, _, factory, _, _ = clients
    h = register(a)
    batch = import_inventory(a, h)
    assert a.post(f"/api/v1/imports/{batch}/apply", headers=h).json()["already_applied"]
    when = utcnow().isoformat()
    for status, returned, expected in [
        ("preparing", 0, 8),
        ("shipping", 0, 8),
        ("completed", 2, 6),
        ("cancelled", 0, 0),
    ]:
        value = preview(
            a,
            h,
            "sales",
            f"source,order_id,line_id,sku,sold_at,quantity,status,returned_quantity\nsite,order-1,line-1,001,{when},8,{status},{returned}\n",
        )
        assert value.status_code == 200, value.text
        assert a.post(f"/api/v1/imports/{value.json()['id']}/apply", headers=h).status_code == 200
        rows = a.get("/api/v1/variants").json()["rows"]
        assert rows[0]["net_units"] == expected
        assert rows[0]["available"] == 2
        assert (rows[0]["priority"] == 1) is (expected > 0)
    with factory() as db:
        saved = db.get(ImportBatch, UUID(batch))
        assert saved.payload is None


def test_foreign_workspace_ids_and_previews_are_denied(clients):
    a, b, _, _, _ = clients
    ha, hb = register(a), register(b, "b")
    batch = import_inventory(a, ha)
    category = a.get("/api/v1/categories").json()[0]
    row = a.get("/api/v1/variants").json()["rows"][0]
    assert (
        b.patch(
            f"/api/v1/categories/{category['id']}", headers=hb, json={"low_max": 1, "high_min": 4}
        ).status_code
        == 404
    )
    assert (
        b.patch(
            f"/api/v1/variants/{row['id']}/replenishment", headers=hb, json={"state": "producing"}
        ).status_code
        == 404
    )
    assert b.post(f"/api/v1/imports/{batch}/apply", headers=hb).status_code == 404
    assert b.get(f"/api/v1/variants?category_id={category['id']}").status_code == 404
    assert b.get("/api/v1/variants").json()["rows"] == []
    assert "Synthetic shoe" not in b.get("/api/v1/account/export").text


def test_failed_preview_is_atomic_and_old_preview_is_rejected(clients):
    a, _, factory, _, _ = clients
    h = register(a)
    bad = preview(
        a,
        h,
        "inventory",
        "sku,name,category,color,size,available\n001,Shoe,Shoes,black,42,2\n002,Shoe,Shoes,black,40,-2\n",
    )
    assert bad.json()["errors"]
    assert a.get("/api/v1/variants").json()["total"] == 0
    good = preview(
        a, h, "inventory", "sku,name,category,color,size,available\n001,Shoe,Shoes,black,42,2\n"
    )
    batch = good.json()["id"]
    with factory() as db:
        from app.db.models import Workspace

        w = db.scalar(select(Workspace))
        w.data_revision += 1
        db.commit()
    assert a.post(f"/api/v1/imports/{batch}/apply", headers=h).status_code == 409


def test_snapshot_dates_thresholds_aggregate_mode_and_production(clients):
    a, _, _, _, _ = clients
    h = register(a)
    import_inventory(a, h)
    stale = preview(
        a,
        h,
        "inventory",
        "sku,name,category,color,size,available\n001,Shoe,Shoes,black,42,0\n",
        snapshot_at=(utcnow() - timedelta(days=2)).isoformat(),
    )
    assert stale.status_code == 409
    day = utcnow().date().isoformat()
    value = preview(
        a, h, "aggregate", f"sku,net_units,period_start,period_end\n001,20,{day},{day}\n"
    )
    assert a.post(f"/api/v1/imports/{value.json()['id']}/apply", headers=h).status_code == 200
    rows = a.get("/api/v1/variants").json()
    assert rows["sales_mode"] == "aggregate" and rows["rows"][0]["net_units"] == 20
    row = rows["rows"][0]
    assert (
        a.patch(
            f"/api/v1/variants/{row['id']}/replenishment", headers=h, json={"state": "producing"}
        ).status_code
        == 200
    )
    assert a.get("/api/v1/variants").json()["priorities"] == 0
    assert a.get("/api/v1/assistant?topic=priorities").json()["items"] == []
    cat = a.get("/api/v1/categories").json()[0]
    assert (
        a.patch(
            f"/api/v1/categories/{cat['id']}", headers=h, json={"low_max": 5, "high_min": 3}
        ).status_code
        == 400
    )
    assert (
        a.patch(
            f"/api/v1/categories/{cat['id']}", headers=h, json={"low_max": 1, "high_min": 4}
        ).status_code
        == 200
    )
    assert a.get("/api/v1/variants").json()["rows"][0]["state"] == "normal"


def test_password_reset_is_one_use_and_invalidates_sessions(clients):
    a, b, _, _, sent = clients
    h = register(a)
    hb = bootstrap(b)
    result = b.post(
        "/api/v1/auth/login", headers=hb, json={"email": "a@example.com", "password": PASSWORD}
    )
    assert result.status_code == 200
    assert (
        a.post(
            "/api/v1/auth/password/request", headers=h, json={"email": "a@example.com"}
        ).status_code
        == 200
    )
    token = sent[-1][1]
    new = "new-long-synthetic-password"
    assert (
        a.post(
            "/api/v1/auth/password/reset", headers=h, json={"token": token, "password": new}
        ).status_code
        == 200
    )
    assert b.get("/api/v1/variants").status_code == 401
    assert (
        a.post(
            "/api/v1/auth/password/reset",
            headers=bootstrap(a),
            json={"token": token, "password": new},
        ).status_code
        == 400
    )
    assert (
        a.post(
            "/api/v1/auth/login",
            headers=bootstrap(a),
            json={"email": "a@example.com", "password": new},
        ).status_code
        == 200
    )


def test_failed_login_rate_is_not_rolled_back(clients):
    a, _, _, _, _ = clients
    h = bootstrap(a)
    values = [
        a.post(
            "/api/v1/auth/login",
            headers=h,
            json={"email": "missing@example.com", "password": "wrong"},
        ).status_code
        for _ in range(11)
    ]
    assert values[:10] == [401] * 10 and values[-1] == 429


def test_expired_session_and_account_deletion_cascade(clients):
    a, b, factory, _, _ = clients
    h = register(a)
    import_inventory(a, h)
    assert PASSWORD not in a.get("/api/v1/account/export").text
    assert (
        a.request(
            "DELETE",
            "/api/v1/account",
            headers=h,
            json={"password": "wrong", "confirmation": "حذف حساب"},
        ).status_code
        == 400
    )
    response = a.request(
        "DELETE",
        "/api/v1/account",
        headers=h,
        json={"password": PASSWORD, "confirmation": "حذف حساب"},
    )
    assert response.status_code == 200
    with factory() as db:
        assert db.scalar(select(Account)) is None
        assert db.scalar(select(Variant)) is None
    register(b, "b")
    with factory() as db:
        session = db.get(BrowserSession, digest(b.cookies.get("anbar_session_dev")))
        session.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert b.get("/api/v1/variants").status_code == 401


def test_xlsx_formula_size_limit_and_export_formula_neutralization(clients):
    a, _, factory, _, _ = clients
    h = register(a)
    wb = Workbook()
    ws = wb.active
    ws.append(["sku", "name", "category", "available"])
    ws.append(["001", "=1+1", "Shoes", 2])
    data = io.BytesIO()
    wb.save(data)
    result = a.post(
        "/api/v1/imports/headers",
        headers=h,
        data={"kind": "inventory"},
        files={"file": ("test.xlsx", data.getvalue())},
    )
    assert result.status_code == 400
    assert a.post("/api/v1/auth/login", headers=h, content=b"x" * 32769).status_code == 413
    import_inventory(a, h)
    with factory() as db:
        v = db.scalar(select(Variant))
        v.name = " =HYPERLINK(1)"
        db.commit()
    response = a.get("/api/v1/export.csv")
    assert "' =HYPERLINK(1)" in response.text


def test_google_bundle_atomic_and_disconnect_invalidates_preview(clients, monkeypatch):
    a, _, factory, _, _ = clients
    h = register(a)
    workspace = a.get("/api/v1/auth/session").json()["account"]["workspace_id"]

    class Credential:
        service_account_email = "dedicated-shop@example.com"

    monkeypatch.setattr(
        sheets, "credentials_for", lambda settings, w: Credential() if str(w) == workspace else None
    )
    day = utcnow().isoformat()
    inventory_available = 2
    monkeypatch.setattr(
        sheets,
        "fetch_values",
        lambda cred, config: [
            [
                ["sku", "name", "category", "color", "size", "available"],
                ["001", "Synthetic shoe", "Shoes", "black", "42", inventory_available],
            ],
            [
                [
                    "source",
                    "order_id",
                    "line_id",
                    "sku",
                    "sold_at",
                    "quantity",
                    "status",
                    "returned_quantity",
                ],
                ["site", "a", "b", "001", day, 10, "shipping", 0],
            ],
        ],
    )
    body = {
        "spreadsheet_id": "synthetic-spreadsheet-id-123",
        "inventory_range": "inventory!A1:Z10001",
        "sales_range": "sales!A1:Z10001",
    }
    assert a.post("/api/v1/sheets/connect", headers=h, json=body).status_code == 200
    result = a.post("/api/v1/sheets/sync", headers=h)
    assert result.status_code == 200, result.text
    batch = result.json()["id"]
    assert a.get("/api/v1/variants").json()["rows"] == []
    result = a.post(f"/api/v1/imports/{batch}/apply", headers=h)
    assert result.status_code == 200, result.text
    row = a.get("/api/v1/variants").json()["rows"][0]
    assert row["net_units"] == 10 and row["available"] == 2
    inventory_available = 7
    pending = a.post("/api/v1/sheets/sync", headers=h).json()["id"]
    original = importing.apply_preview

    def fail_sales(db, workspace_id, batch_id, settings, commit=True):
        child = db.get(ImportBatch, batch_id)
        if child.kind == "sales":
            raise ValueError("Synthetic failure after inventory writes")
        return original(db, workspace_id, batch_id, settings, commit)

    monkeypatch.setattr(importing, "apply_preview", fail_sales)
    assert a.post(f"/api/v1/imports/{pending}/apply", headers=h).status_code == 500
    with factory() as db:
        assert not db.get(ImportBatch, UUID(pending)).applied
        assert db.scalar(select(Variant)).available == 2
    monkeypatch.setattr(importing, "apply_preview", original)
    assert a.delete("/api/v1/sheets/connection", headers=h).status_code == 200
    assert a.post(f"/api/v1/imports/{pending}/apply", headers=h).status_code == 404


def test_production_verification_cookie_and_precreated_account_takeover(clients):
    _, _, _, settings, sent = clients
    settings = settings.model_copy(
        update={
            "app_env": "production",
            "require_email_verification": True,
            "allowed_hosts": "inventory.example",
            "cors_origins": "",
            "public_origin": "https://inventory.example",
        }
    )
    app = create_app(settings)
    client = TestClient(app, base_url=settings.public_origin)

    def headers():
        response = client.get("/api/v1/auth/session")
        return {"Origin": settings.public_origin, "X-CSRF-Token": response.json()["csrf_token"]}

    initial = client.get("/api/v1/auth/session")
    cookie = initial.headers["set-cookie"]
    assert "__Host-session=" in cookie and "Secure" in cookie and "HttpOnly" in cookie
    assert "SameSite=lax" in cookie and "Path=/" in cookie and "Domain=" not in cookie
    body = {
        "email": "owner@example.com",
        "password": PASSWORD,
        "workspace_name": "Shop",
        "accepted_policy": True,
        "policy_version": POLICY_VERSION,
    }
    assert client.post("/api/v1/auth/register", headers=headers(), json=body).json()[
        "verification_required"
    ]
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=headers(),
            json={"email": body["email"], "password": PASSWORD},
        ).status_code
        == 401
    )
    token = sent[-1][1]
    new_password = "fresh-owner-only-password-2026"
    activation = {
        "token": token,
        "password": new_password,
        "accepted_policy": True,
        "policy_version": POLICY_VERSION,
    }
    assert client.post("/api/v1/auth/verify", headers=headers(), json=activation).status_code == 200
    assert client.post("/api/v1/auth/verify", headers=headers(), json=activation).status_code == 400
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=headers(),
            json={"email": body["email"], "password": PASSWORD},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=headers(),
            json={"email": body["email"], "password": new_password},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/dashboard").status_code == 200
    client.close()
    app.state.db_factory.kw["bind"].dispose()


def test_valid_excel_numeric_size_encrypted_preview_and_jalali_sales(clients):
    a, _, factory, settings, _ = clients
    h = register(a)
    wb = Workbook()
    wb.active.append(["sku", "name", "category", "size", "available", "customer_phone"])
    wb.active.append(["0001", "Synthetic", "Shoes", 42, 1, "DO-NOT-STORE-SYNTHETIC-PII"])
    data = io.BytesIO()
    wb.save(data)
    result = a.post(
        "/api/v1/imports/preview",
        headers=h,
        data={
            "kind": "inventory",
            "mapping": json.dumps({f: f for f in ["sku", "name", "category", "size", "available"]}),
        },
        files={"file": ("synthetic.xlsx", data.getvalue())},
    )
    assert result.status_code == 200, result.text
    assert result.json()["sample"][0]["size"] == "42"
    from app.security import decrypt

    with factory() as db:
        stored = db.get(ImportBatch, UUID(result.json()["id"]))
        assert "Synthetic" not in stored.payload
        assert "DO-NOT-STORE" not in json.dumps(decrypt(settings, stored.payload))
    assert a.post(f"/api/v1/imports/{result.json()['id']}/apply", headers=h).status_code == 200
    sales = preview(
        a,
        h,
        "sales",
        "source,order_id,line_id,sku,sold_at,quantity,status,returned_quantity\n"
        "site,1,1,0001,۱۴۰۵/۰۷/۲۰,۶,در حال ارسال,۱\n",
        calendar="jalali",
    )
    assert sales.status_code == 200, sales.text
    assert sales.json()["sample"][0]["sold_at"].startswith("2026-10-11T20:30")


def test_password_change_revokes_other_sessions(clients):
    a, b, _, _, _ = clients
    h = register(a)
    assert (
        b.post(
            "/api/v1/auth/login",
            headers=bootstrap(b),
            json={"email": "a@example.com", "password": PASSWORD},
        ).status_code
        == 200
    )
    result = a.post(
        "/api/v1/auth/password/change",
        headers=h,
        json={"current_password": PASSWORD, "password": "new-strong-synthetic-password"},
    )
    assert result.status_code == 200, result.text
    assert a.get("/api/v1/dashboard").status_code == 200
    assert b.get("/api/v1/dashboard").status_code == 401


def test_encrypted_backup_restore_preserves_deletion_and_expiry(clients, tmp_path):
    a, _, factory, settings, _ = clients
    h = register(a)
    import_inventory(a, h)
    saved = backup(settings, tmp_path)
    assert not saved.read_bytes().startswith(b"PGDMP")
    assert PASSWORD.encode() not in saved.read_bytes()
    with pytest.raises(RuntimeError, match="confirm-restore"):
        restore(settings, saved, False)
    response = a.request(
        "DELETE",
        "/api/v1/account",
        headers=h,
        json={"password": PASSWORD, "confirmation": "حذف حساب"},
    )
    assert response.status_code == 200
    restore(settings, saved, True)
    with factory() as db:
        assert db.scalar(select(Account)) is None
        assert db.scalar(select(Variant)) is None
        assert db.scalar(select(DeletionMarker)) is not None
        assert db.scalar(select(BrowserSession)) is None
    corrupt = tmp_path / "tampered.anbar"
    corrupt.write_bytes(saved.read_bytes()[:-5] + b"XXXXX")
    with pytest.raises(RuntimeError, match="authentication failed"):
        restore(settings, corrupt, True)
    old = tmp_path / "20200101T000000.anbar"
    old.write_bytes(b"synthetic")
    os.utime(old, (1, 1))
    unrelated = tmp_path / "keep.txt"
    unrelated.write_text("keep")
    expire_backups(settings, tmp_path)
    assert not old.exists() and saved.exists() and unrelated.exists()


def test_expired_previews_and_minimal_audit_are_cleaned_without_shop_data(clients):
    from app.db.models import AuditEvent

    a, _, factory, _, _ = clients
    h = register(a)
    import_inventory(a, h)
    pending = preview(
        a,
        h,
        "inventory",
        "sku,name,category,color,size,available\n001,Synthetic,Shoes,black,42,3\n",
    )
    with factory() as db:
        row = db.get(ImportBatch, UUID(pending.json()["id"]))
        row.expires_at = utcnow() - timedelta(hours=1)
        for event in db.scalars(select(AuditEvent)):
            event.created_at = utcnow() - timedelta(days=91)
        db.commit()
    assert a.post(f"/api/v1/imports/{pending.json()['id']}/apply", headers=h).status_code == 410
    cleanup(factory)
    with factory() as db:
        assert db.get(ImportBatch, UUID(pending.json()["id"])) is None
        assert db.scalar(select(AuditEvent)) is None
        assert db.scalar(select(Variant)).available == 2
