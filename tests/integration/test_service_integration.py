import uuid

import psycopg

from tests.system_support import (
    BOOKING_DATABASE_URL,
    FLIGHT_DATABASE_URL,
    cleanup,
    create_booking,
    create_flight,
    post_booking,
)


def test_booking_api_calls_flight_service_and_persists_data() -> None:
    flight = create_flight()
    booking = None
    try:
        booking = create_booking(flight["id"], seats=2)
        assert booking["status"] == "CONFIRMED"
        assert booking["total_price"] == 5001.0

        with psycopg.connect(BOOKING_DATABASE_URL) as connection:
            booking_status = connection.execute(
                "SELECT status FROM bookings WHERE id = %s", (booking["id"],)
            ).fetchone()
        with psycopg.connect(FLIGHT_DATABASE_URL) as connection:
            row_reservation = connection.execute(
                "SELECT seat_count, status FROM seat_reservations WHERE booking_id = %s",
                (booking["id"],),
            ).fetchone()
        assert booking_status == ("CONFIRMED",)
        assert row_reservation == (2, "ACTIVE")
    finally:
        cleanup(flight["id"], booking["id"] if booking else None)


def test_rejects_booking_more_seats_than_remain_without_changing_state() -> None:
    flight = create_flight(total_seats=3)
    booking = None
    try:
        booking = create_booking(flight["id"], seats=2)

        rejected = post_booking(flight["id"], seats=2)
        assert rejected.status_code == 409
        assert rejected.json()["detail"] == "not enough seats"

        with psycopg.connect(BOOKING_DATABASE_URL) as connection:
            booking_count = connection.execute(
                "SELECT COUNT(*) FROM bookings WHERE flight_id = %s", (flight["id"],)
            ).fetchone()
        with psycopg.connect(FLIGHT_DATABASE_URL) as connection:
            row = connection.execute(
                """
                SELECT f.available_seats, COUNT(r.id)
                FROM flights f
                LEFT JOIN seat_reservations r ON r.flight_id = f.id
                WHERE f.id = %s
                GROUP BY f.available_seats
                """,
                (flight["id"],),
            ).fetchone()
        assert booking_count == (1,)
        assert row == (1, 1)
    finally:
        cleanup(flight["id"], booking["id"] if booking else None)


def test_rejects_booking_for_nonexistent_flight_without_persisting_booking() -> None:
    missing_flight_id = str(uuid.uuid4())

    rejected = post_booking(missing_flight_id)

    assert rejected.status_code == 404
    assert rejected.json()["detail"] == "flight not found"
    with psycopg.connect(BOOKING_DATABASE_URL) as connection:
        booking_count = connection.execute(
            "SELECT COUNT(*) FROM bookings WHERE flight_id = %s", (missing_flight_id,)
        ).fetchone()
    assert booking_count == (0,)
