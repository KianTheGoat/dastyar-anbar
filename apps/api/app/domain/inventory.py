from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


def require_count(value: int, field: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer")


class StockState(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True)
class Thresholds:
    low_max: int
    high_min: int

    def __post_init__(self) -> None:
        require_count(self.low_max, "low_max")
        require_count(self.high_min, "high_min")
        if self.high_min <= self.low_max:
            raise ValueError("high_min must exceed low_max")


def classify(available: int, thresholds: Thresholds) -> StockState:
    require_count(available, "available")
    if available <= thresholds.low_max:
        return StockState.LOW
    if available >= thresholds.high_min:
        return StockState.HIGH
    return StockState.NORMAL


def net_sold(quantity: int, returned: int, status: str) -> int:
    require_count(quantity, "quantity")
    require_count(returned, "returned")
    if returned > quantity:
        raise ValueError("returned cannot exceed quantity")
    known = {"preparing", "shipping", "completed", "pending", "cancelled", "refunded"}
    if status not in known:
        raise ValueError("Unknown sale status; map source labels explicitly")
    return quantity - returned if status in {"preparing", "shipping", "completed"} else 0


@dataclass(frozen=True)
class VariantSummary:
    sku: str
    available: int
    net_units: int
    thresholds: Thresholds

    def __post_init__(self) -> None:
        if not isinstance(self.sku, str) or not self.sku.strip():
            raise ValueError("sku is required")
        require_count(self.available, "available")
        require_count(self.net_units, "net_units")

    @property
    def needs_review(self) -> bool:
        return classify(self.available, self.thresholds) == StockState.LOW and self.net_units == 0


def rank_replenishment(variants: Iterable[VariantSummary]) -> list[VariantSummary]:
    """Caller supplies summaries for exactly one authorized workspace and period."""
    candidates = [
        item
        for item in variants
        if classify(item.available, item.thresholds) == StockState.LOW and item.net_units > 0
    ]
    return sorted(candidates, key=lambda item: (-item.net_units, item.available, item.sku))
