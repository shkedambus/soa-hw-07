from decimal import Decimal, ROUND_HALF_UP


def calculate_total_price(price: float, seat_count: int) -> Decimal:
    if price <= 0 or seat_count <= 0:
        raise ValueError("price and seat_count must be positive")
    return (Decimal(str(price)) * Decimal(seat_count)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
