import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app


def test_health_is_data_free_and_sets_no_cookie():
    client = TestClient(create_app(Settings(app_env="test", allowed_hosts="testserver")))
    response = client.get("/api/health")
    assert response.json() == {"status": "ok", "stage": "foundation"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers
    assert client.get("/api/v1/variants").status_code == 404
    assert client.get("/api/health", headers={"host": "untrusted.example"}).status_code == 400


def test_production_is_explicit_and_docs_disabled():
    with pytest.raises(ValidationError):
        Settings(app_env="production")
    client = TestClient(
        create_app(
            Settings(
                app_env="production",
                allowed_hosts="inventory.example",
                cors_origins="",
            )
        ),
        base_url="https://inventory.example",
    )
    assert client.get("/api/docs").status_code == 404
    assert client.get("/api/openapi.json").status_code == 404
    assert "frame-ancestors 'none'" in client.get("/api/health").headers["content-security-policy"]


def test_wildcard_cors_is_rejected():
    with pytest.raises(ValidationError):
        Settings(cors_origins="*")
