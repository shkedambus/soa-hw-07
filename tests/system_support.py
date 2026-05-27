import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
import requests


API_URL = os.getenv("API_URL", "http://booking-service:8080")
BOOKING_DATABASE_URL = os.environ["BOOKING_DATABASE_URL"]
FLIGHT_DATABASE_URL = os.environ["FLIGHT_DATABASE_URL"]


def create_flight(total_seats: int = 12) -> dict:
    suffix = uuid.uuid4().hex[:10].upper()
    departure = datetime.now(timezone.utc) + timedelta(days=2)
    response = requests.post(
        f"{API_URL}/flights",
        json={
            "flight_number": f"T{suffix}",
            "origin": "DME",
            "destination": "KZN",
            "departure_time": departure.isoformat(),
            "arrival_time": (departure + timedelta(hours=2)).isoformat(),
            "total_seats": total_seats,
            "price": 2500.50,
        },
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def post_booking(flight_id: str, seats: int = 2) -> requests.Response:
    return requests.post(
        f"{API_URL}/bookings",
        json={
            "user_id": f"test-{uuid.uuid4().hex[:8]}",
            "flight_id": flight_id,
            "passenger_name": "Test Passenger",
            "passenger_email": "passenger@example.com",
            "seat_count": seats,
        },
        timeout=5,
    )


def create_booking(flight_id: str, seats: int = 2) -> dict:
    response = post_booking(flight_id, seats)
    response.raise_for_status()
    return response.json()


def cleanup(flight_id: str, booking_id: str | None = None) -> None:
    if booking_id:
        with psycopg.connect(BOOKING_DATABASE_URL) as connection:
            connection.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
        with psycopg.connect(FLIGHT_DATABASE_URL) as connection:
            connection.execute(
                "DELETE FROM seat_reservations WHERE booking_id = %s", (booking_id,)
            )
    with psycopg.connect(FLIGHT_DATABASE_URL) as connection:
        connection.execute("DELETE FROM flights WHERE id = %s", (flight_id,))
