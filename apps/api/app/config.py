from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

POLICY_VERSION = "2026-10-12"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    allowed_hosts: str = "localhost,127.0.0.1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    public_origin: str = "http://127.0.0.1:5173"
    database_url: SecretStr | None = None
    app_secret: SecretStr | None = None
    operator_name: str = "مالک مجموعهٔ دستیار"
    privacy_contact: str = ""
    operating_country: str = ""
    hosting_region: str = ""
    subprocessors: str = ""
    backup_retention_days: int = 30
    require_email_verification: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr | None = None
    smtp_from: str = ""
    google_credentials_dir: str = ""

    @property
    def hosts(self) -> list[str]:
        return [value.strip() for value in self.allowed_hosts.split(",") if value.strip()]

    @property
    def origins(self) -> list[str]:
        return list(
            dict.fromkeys(
                [self.public_origin]
                + [value.strip() for value in self.cors_origins.split(",") if value.strip()]
            )
        )

    @property
    def cookie_name(self) -> str:
        return "__Host-session" if self.app_env == "production" else "anbar_session_dev"

    @property
    def configured(self) -> bool:
        return self.database_url is not None and self.app_secret is not None

    @model_validator(mode="after")
    def validate_network_settings(self) -> "Settings":
        if not self.hosts or any("*" in host or "/" in host for host in self.hosts):
            raise ValueError("Explicit hostnames are required")
        for origin in self.origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
            ):
                raise ValueError("Origins must be exact HTTP(S) origins without paths")
        if self.app_secret and len(self.app_secret.get_secret_value()) < 32:
            raise ValueError("APP_SECRET requires at least 32 characters")
        if self.database_url and not self.database_url.get_secret_value().startswith(
            "postgresql+psycopg://"
        ):
            raise ValueError("PostgreSQL psycopg URL required")
        if not 1 <= self.backup_retention_days <= 365:
            raise ValueError("Invalid backup retention")
        if self.smtp_user and not self.smtp_password:
            raise ValueError("SMTP authentication requires a password")
        if self.app_env == "production":
            if (
                not self.configured
                or not self.privacy_contact
                or not self.operating_country
                or not self.hosting_region
                or not self.subprocessors
            ):
                raise ValueError(
                    "Production identity, contact, hosting and secrets must be configured"
                )
            if any(host in {"localhost", "127.0.0.1", "testserver"} for host in self.hosts):
                raise ValueError("Production requires its actual hostnames")
            if any(not origin.startswith("https://") for origin in self.origins):
                raise ValueError("Production CORS origins require HTTPS")
            if not self.require_email_verification or not self.smtp_host or not self.smtp_from:
                raise ValueError("Production requires email verification and SMTP")
        return self
