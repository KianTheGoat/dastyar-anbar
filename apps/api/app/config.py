from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    allowed_hosts: str = "localhost,127.0.0.1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def hosts(self) -> list[str]:
        return [value.strip() for value in self.allowed_hosts.split(",") if value.strip()]

    @property
    def origins(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]

    @model_validator(mode="after")
    def validate_network_settings(self) -> "Settings":
        if not self.hosts or any("*" in host or "/" in host for host in self.hosts):
            raise ValueError("Explicit hostnames are required")
        if any(origin == "*" for origin in self.origins):
            raise ValueError("Wildcard CORS is prohibited")
        if self.app_env == "production":
            if any(host in {"localhost", "127.0.0.1", "testserver"} for host in self.hosts):
                raise ValueError("Production requires its actual hostnames")
            if any(not origin.startswith("https://") for origin in self.origins):
                raise ValueError("Production CORS origins require HTTPS")
        return self
