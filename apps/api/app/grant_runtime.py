"""Run once with migration-owner credentials after migrations, not inside the API."""

import os

from sqlalchemy import create_engine, text

from app.db.models import Base


def main():
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as db:
        db.execute(text("GRANT USAGE ON SCHEMA public TO anbar_app"))
        for table in Base.metadata.sorted_tables:
            # These names are static application metadata, not user-provided identifiers.
            db.execute(text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON "{table.name}" TO anbar_app'))
    engine.dispose()


if __name__ == "__main__":
    main()
