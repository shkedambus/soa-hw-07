import psycopg

from tests.system_support import (
    BOOKING_DATABASE_URL,
    FLIGHT_DATABASE_URL,
    cleanup,
    create_booking,
    create_flight,
)


def test_booking_api_calls_flight_service_and_persists_data() -> None:
    flight = create_flight()
    booking = None
    try:
        booking = create_booking(flight["id"], seats=2)
        assert booking["status"] == "CONFIRMED"
        assert booking["total_price"] == 5001.0

        with psycopg.connect(BOOKING_DATABASE_URL) as connection:
            row = connection.execute(
                "SELECT status FROM bookings WHERE id = %s", (booking["id"],)
            ).fetchone()
        with psycopg.connect(FLIGHT_DATABASE_URL) as connection:
            row_reservation = connection.execute(
                "SELECT seat_count, status FROM seat_reservations WHERE booking_id = %s",
                (booking["id"],),
            ).fetchone()
        assert row == ("CONFIRMED",)
        assert row_reservation == (2, "ACTIVE")
    finally:
        cleanup(flight["id"], booking["id"] if booking else None)
