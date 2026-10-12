import os

from alembic import context
from sqlalchemy import create_engine, pool

from app.db.models import Base

target_metadata = Base.metadata
database_url = os.environ.get("DATABASE_URL")
if not database_url or not database_url.startswith("postgresql+psycopg://"):
    raise RuntimeError("Set DATABASE_URL to a PostgreSQL psycopg connection")

if context.is_offline_mode():
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(database_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
