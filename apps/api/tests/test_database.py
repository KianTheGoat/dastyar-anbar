import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.exc import IntegrityError

from app.db.models import Category, SaleLine, Variant, Workspace

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="Dedicated PostgreSQL test DB required")


@pytest.fixture
def db():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()
    engine.dispose()


def seed(db):
    first, second, category, variant = uuid4(), uuid4(), uuid4(), uuid4()
    db.execute(insert(Workspace), [{"id": first, "name": "A"}, {"id": second, "name": "B"}])
    db.execute(
        insert(Category),
        {
            "id": category,
            "workspace_id": first,
            "name": "Shoes",
            "low_max": 3,
            "high_min": 5,
        },
    )
    db.execute(insert(Variant), variant_values(first, category, variant))
    return first, second, category, variant


def variant_values(workspace, category, variant_id):
    return {
        "id": variant_id,
        "workspace_id": workspace,
        "category_id": category,
        "sku": "001",
        "name": "Synthetic shoe",
        "color": "black",
        "size": "42",
        "available": 2,
        "inventory_updated_at": datetime.now(UTC),
    }


def test_variant_cannot_reference_another_workspace_category(db):
    _, second, category, _ = seed(db)
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(insert(Variant), variant_values(second, category, uuid4()))


def test_sku_unique_per_workspace_not_globally(db):
    first, second, category, _ = seed(db)
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(insert(Variant), variant_values(first, category, uuid4()))
    other_category = uuid4()
    db.execute(
        insert(Category),
        {
            "id": other_category,
            "workspace_id": second,
            "name": "Shoes",
            "low_max": 3,
            "high_min": 5,
        },
    )
    db.execute(insert(Variant), variant_values(second, other_category, uuid4()))


def test_sale_cannot_reference_other_workspace_and_line_is_unique(db):
    first, second, _, variant = seed(db)
    sale = {
        "id": uuid4(),
        "workspace_id": second,
        "variant_id": variant,
        "source": "csv",
        "external_order_id": "order-1",
        "external_line_id": "line-1",
        "sold_at": datetime.now(UTC),
        "quantity": 3,
        "returned_quantity": 0,
        "status": "preparing",
    }
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(insert(SaleLine), sale)
    sale["workspace_id"] = first
    db.execute(insert(SaleLine), sale)
    sale["id"] = uuid4()
    sale["status"] = "shipping"
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(insert(SaleLine), sale)


def test_database_rejects_overlapping_thresholds(db):
    first, _, _, _ = seed(db)
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(
            insert(Category),
            {
                "id": uuid4(),
                "workspace_id": first,
                "name": "Invalid",
                "low_max": 5,
                "high_min": 3,
            },
        )
