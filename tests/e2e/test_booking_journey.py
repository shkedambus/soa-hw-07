import psycopg
import requests

from tests.system_support import API_URL, FLIGHT_DATABASE_URL, cleanup, create_booking, create_flight


def test_user_books_and_cancels_seats_end_to_end() -> None:
    flight = create_flight(total_seats=8)
    booking = None
    try:
        booking = create_booking(flight["id"], seats=3)
        after_booking = requests.get(f"{API_URL}/flights/{flight['id']}", timeout=5)
        assert after_booking.status_code == 200
        assert after_booking.json()["available_seats"] == 5

        cancelled = requests.post(
            f"{API_URL}/bookings/{booking['id']}/cancel", timeout=5
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "CANCELLED"

        with psycopg.connect(FLIGHT_DATABASE_URL) as connection:
            row = connection.execute(
                """
                SELECT f.available_seats, r.status
                FROM flights f
                JOIN seat_reservations r ON r.flight_id = f.id
                WHERE r.booking_id = %s
                """,
                (booking["id"],),
            ).fetchone()
        assert row == (8, "RELEASED")
    finally:
        cleanup(flight["id"], booking["id"] if booking else None)
