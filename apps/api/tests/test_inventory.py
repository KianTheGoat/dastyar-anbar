import pytest

from app.domain.inventory import (
    StockState,
    Thresholds,
    VariantSummary,
    classify,
    net_sold,
    rank_replenishment,
)


@pytest.mark.parametrize("count,state", [(0, "low"), (3, "low"), (4, "normal"), (5, "high")])
def test_inclusive_category_boundaries(count, state):
    assert classify(count, Thresholds(3, 5)) == StockState(state)


@pytest.mark.parametrize("count", [-1, 1.5, True, float("nan"), "3"])
def test_invalid_counts_fail(count):
    with pytest.raises(ValueError):
        classify(count, Thresholds(3, 5))


@pytest.mark.parametrize("low,high", [(3, 3), (4, 2), (-1, 5)])
def test_invalid_thresholds_fail(low, high):
    with pytest.raises(ValueError):
        Thresholds(low, high)


def test_ranking_sales_then_stock_then_sku_and_no_sales_review():
    thresholds = Thresholds(3, 5)
    values = [
        VariantSummary("D", 0, 20, thresholds),
        VariantSummary("B", 1, 45, thresholds),
        VariantSummary("A", 1, 45, thresholds),
        VariantSummary("C", 2, 45, thresholds),
        VariantSummary("HIGH", 5, 100, thresholds),
        VariantSummary("NEW", 0, 0, thresholds),
    ]
    assert [row.sku for row in rank_replenishment(values)] == ["A", "B", "C", "D"]
    assert values[-1].needs_review


@pytest.mark.parametrize("status", ["preparing", "shipping", "completed"])
def test_eligible_sale_states_and_partial_returns(status):
    assert net_sold(5, 2, status) == 3


@pytest.mark.parametrize("status", ["pending", "cancelled", "refunded"])
def test_excluded_sale_states(status):
    assert net_sold(5, 0, status) == 0


def test_unknown_status_and_impossible_returns_fail():
    with pytest.raises(ValueError):
        net_sold(1, 2, "completed")
    with pytest.raises(ValueError):
        net_sold(1, 0, "unmapped")
