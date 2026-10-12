from collections.abc import Generator

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session


def get_db(request: Request) -> Generator[Session]:
    factory = request.app.state.db_factory
    if factory is None:
        raise HTTPException(503, "service_not_configured")
    with factory() as db:
        try:
            yield db
        finally:
            db.rollback()
