from datetime import datetime


def validate_new_flight(
    origin: str,
    destination: str,
    departure_time: datetime,
    arrival_time: datetime,
    total_seats: int,
    price: float,
) -> None:
    if origin == destination:
        raise ValueError("origin and destination must differ")
    if arrival_time <= departure_time:
        raise ValueError("arrival must be after departure")
    if total_seats <= 0 or price <= 0:
        raise ValueError("seats and price must be positive")


def ensure_seats_available(available_seats: int, requested_seats: int) -> None:
    if requested_seats <= 0:
        raise ValueError("seat count must be positive")
    if available_seats < requested_seats:
        raise LookupError("not enough seats")
