from decimal import Decimal

import pytest

from app.domain import calculate_total_price


def test_calculates_price_snapshot() -> None:
    assert calculate_total_price(1499.95, 2) == Decimal("2999.90")


@pytest.mark.parametrize(("price", "seats"), [(0, 1), (100, 0), (-1, 2)])
def test_rejects_invalid_price_or_quantity(price: float, seats: int) -> None:
    with pytest.raises(ValueError):
        calculate_total_price(price, seats)
