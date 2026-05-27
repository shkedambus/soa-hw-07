from datetime import datetime, timedelta, timezone

import pytest

from app.domain import ensure_seats_available, validate_new_flight


def test_accepts_valid_new_flight() -> None:
    departure = datetime.now(timezone.utc)
    validate_new_flight("SVO", "LED", departure, departure + timedelta(hours=2), 10, 1.5)


def test_rejects_same_airport() -> None:
    departure = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        validate_new_flight("SVO", "SVO", departure, departure + timedelta(hours=2), 10, 1.5)


def test_rejects_reservation_over_available_seats() -> None:
    with pytest.raises(LookupError):
        ensure_seats_available(1, 2)
