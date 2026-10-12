"""Encrypted bounded backups. Restore is an explicit maintenance action."""

import argparse
import os
import re
import subprocess
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from cryptography.fernet import InvalidToken
from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import DeletionMarker, Workspace
from app.security import cipher, digest, utcnow

MAX_DUMP = 128 * 1024 * 1024


def pg_environment(settings):
    parsed = urlsplit(
        settings.database_url.get_secret_value().replace("postgresql+psycopg", "postgresql", 1)
    )
    environment = os.environ | {
        "PGHOST": parsed.hostname or "",
        "PGPORT": str(parsed.port or 5432),
        "PGUSER": unquote(parsed.username or ""),
        "PGPASSWORD": unquote(parsed.password or ""),
        "PGDATABASE": unquote(parsed.path.lstrip("/")),
        "PGCONNECT_TIMEOUT": "10",
        "PGOPTIONS": "-c statement_timeout=60000",
    }
    for key, name in [("sslmode", "PGSSLMODE"), ("sslrootcert", "PGSSLROOTCERT")]:
        values = parse_qs(parsed.query).get(key)
        if values:
            environment[name] = values[-1]
    return environment


def pg_command(program: str, arguments: list[str]) -> list[str]:
    # CI may use PostgreSQL tools in its own disposable database container.
    container = os.environ.get("PG_TOOL_CONTAINER")
    if not container:
        return [program, *arguments]
    flags = [
        part
        for key in [
            "PGHOST",
            "PGPORT",
            "PGUSER",
            "PGPASSWORD",
            "PGDATABASE",
            "PGCONNECT_TIMEOUT",
            "PGOPTIONS",
        ]
        for part in ["-e", key]
    ]
    return ["docker", "exec", "-i", *flags, container, program, *arguments]


def backup(settings: Settings, directory: Path) -> Path:
    root = directory.resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with subprocess.Popen(
        pg_command(
            "pg_dump",
            ["--format=custom", "--no-owner", "--no-privileges", "--lock-wait-timeout=10s"],
        ),
        env=pg_environment(settings),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    ) as process:
        data = process.stdout.read(MAX_DUMP + 1)
        if len(data) > MAX_DUMP:
            process.kill()
            raise RuntimeError("Backup exceeds pilot size limit")
        if process.wait(timeout=60) != 0:
            raise RuntimeError("Database backup failed")
    target = root / (utcnow().strftime("%Y%m%dT%H%M%S%f") + ".anbar")
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as file:
        file.write(cipher(settings).encrypt(data))
    expire_backups(settings, root)
    return target


def expire_backups(settings: Settings, directory: Path):
    cutoff = utcnow() - timedelta(days=settings.backup_retention_days)
    for file in directory.iterdir():
        if (
            re.fullmatch(r"\d{8}T\d{6}(?:\d{6})?\.anbar", file.name)
            and file.is_file()
            and not file.is_symlink()
            and file.resolve().parent == directory.resolve()
            and file.stat().st_mtime < cutoff.timestamp()
        ):
            file.unlink()


def restore(settings: Settings, filename: Path, confirmed: bool) -> None:
    if not confirmed:
        raise RuntimeError("Restore requires --confirm-restore with API stopped")
    if filename.stat().st_size > MAX_DUMP * 2:
        raise RuntimeError("Backup exceeds size limit")
    try:
        data = cipher(settings).decrypt(filename.read_bytes())
    except InvalidToken:
        raise RuntimeError("Backup authentication failed") from None
    engine = create_engine(settings.database_url.get_secret_value())
    with Session(engine) as db:
        markers = list(
            db.execute(
                select(DeletionMarker.workspace_hash, DeletionMarker.expires_at).where(
                    DeletionMarker.expires_at > utcnow()
                )
            ).all()
        )
    result = subprocess.run(
        pg_command(
            "pg_restore",
            [
                "--clean",
                "--if-exists",
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                pg_environment(settings)["PGDATABASE"],
            ],
        ),
        env=pg_environment(settings),
        input=data,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
    )
    if result.returncode:
        raise RuntimeError("Restore failed; keep API stopped")
    with Session(engine) as db:
        for hashed, expiry in markers:
            db.execute(
                insert(DeletionMarker)
                .values(workspace_hash=hashed, expires_at=expiry)
                .on_conflict_do_update(
                    index_elements=[DeletionMarker.workspace_hash], set_={"expires_at": expiry}
                )
            )
        all_markers = set(
            db.scalars(
                select(DeletionMarker.workspace_hash).where(DeletionMarker.expires_at > utcnow())
            )
        )
        for workspace in db.scalars(select(Workspace)):
            if digest(str(workspace.id)) in all_markers:
                db.delete(workspace)
        db.execute(text("DELETE FROM browser_sessions"))
        db.execute(text("DELETE FROM action_tokens"))
        db.commit()
    engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["create", "restore", "daemon"])
    parser.add_argument("--directory", default="/backups")
    parser.add_argument("--file")
    parser.add_argument("--confirm-restore", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    if not settings.configured:
        raise RuntimeError("Backup credentials and encryption key required")
    if args.action == "restore":
        if not args.file:
            raise RuntimeError("Backup file required")
        restore(settings, Path(args.file), args.confirm_restore)
    elif args.action == "create":
        backup(settings, Path(args.directory))
    else:
        while True:
            try:
                backup(settings, Path(args.directory))
            except Exception:
                print("backup_failed", flush=True)
            time.sleep(24 * 3600)


if __name__ == "__main__":
    main()
