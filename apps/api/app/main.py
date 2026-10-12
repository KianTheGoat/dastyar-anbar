import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import auth, dashboard, import_routes, sheets
from app.body_limit import BodyLimitMiddleware
from app.config import POLICY_VERSION, Settings
from app.importing import FIELDS
from app.maintenance import cleanup


def create_app(settings: Settings | None = None) -> FastAPI:
    try:
        settings = settings or Settings()
    except ValidationError:
        raise RuntimeError(
            "Unsafe or incomplete runtime configuration; see configuration examples"
        ) from None
    production = settings.app_env == "production"
    engine = (
        create_engine(
            settings.database_url.get_secret_value(),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
        )
        if settings.database_url
        else None
    )
    factory = (
        sessionmaker(engine, expire_on_commit=False) if engine and settings.app_secret else None
    )

    @asynccontextmanager
    async def lifespan(application):
        async def janitor():
            while True:
                try:
                    await asyncio.to_thread(cleanup, factory)
                except Exception:
                    logging.getLogger("anbar").warning("maintenance_failed")
                await asyncio.sleep(3600)

        task = asyncio.create_task(janitor()) if factory else None
        yield
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if engine:
            engine.dispose()

    application = FastAPI(
        title="Dastyar Anbar",
        docs_url=None if production else "/api/docs",
        redoc_url=None,
        openapi_url=None if production else "/api/openapi.json",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.db_factory = factory
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.hosts)
    application.add_middleware(BodyLimitMiddleware)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, exception):
        return JSONResponse(
            {
                "detail": "validation_failed",
                "errors": [
                    {"field": ".".join(str(x) for x in e["loc"] if x != "body"), "code": e["type"]}
                    for e in exception.errors()[:30]
                ],
            },
            status_code=422,
        )

    @application.middleware("http")
    async def security_headers(request, call_next):
        request_id = str(uuid4())
        try:
            response = await call_next(request)
        except IntegrityError:
            response = JSONResponse({"detail": "data_conflict"}, status_code=409)
        except Exception:
            logging.getLogger("anbar").error("request_failed %s", request_id)
            response = JSONResponse({"detail": "request_failed"}, status_code=500)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        if production:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            )
        return response

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "stage": "mvp"}

    @application.get("/api/ready")
    def ready():
        if not factory:
            return JSONResponse({"status": "not_configured"}, status_code=503)
        try:
            with factory() as db:
                db.execute(text("SELECT 1 FROM accounts LIMIT 1"))
            return {"status": "ready"}
        except Exception:
            return JSONResponse({"status": "not_ready"}, status_code=503)

    @application.get("/api/meta")
    def metadata():
        return {
            "product": "دستیار انبار",
            "suite": "دستیار",
            "policy_version": POLICY_VERSION,
            "operator_name": settings.operator_name,
            "privacy_contact": settings.privacy_contact,
            "operating_country": settings.operating_country,
            "hosting_region": settings.hosting_region,
            "subprocessors": settings.subprocessors,
            "backup_retention_days": settings.backup_retention_days,
            "configured": settings.configured,
            "verification_required": settings.require_email_verification,
            "password_recovery_available": bool(settings.smtp_host),
            "cookie_name": settings.cookie_name,
            "session_days": 7,
            "idle_hours": 12,
        }

    @application.get("/api/templates/{kind}.csv")
    def template(kind: str):
        if kind not in FIELDS:
            return JSONResponse({"detail": "not_found"}, status_code=404)
        return Response(
            "\ufeff" + ",".join(FIELDS[kind]) + "\r\n",
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{kind}-template.csv"'},
        )

    for router in [auth.router, dashboard.router, import_routes.router, sheets.router]:
        application.include_router(router)

    return application


app = create_app()
