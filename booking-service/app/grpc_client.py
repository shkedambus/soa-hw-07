from datetime import datetime, timezone
from uuid import UUID

import flight_pb2
import flight_pb2_grpc
import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from app.config import settings
from app.schemas import CreateFlightRequest


class FlightClient:
    def __init__(self) -> None:
        channel = grpc.insecure_channel(settings.flight_grpc_target)
        self.stub = flight_pb2_grpc.FlightServiceStub(channel)
        self.timeout = settings.grpc_timeout_seconds

    def create_flight(self, payload: CreateFlightRequest) -> dict:
        response = self.stub.CreateFlight(
            flight_pb2.CreateFlightRequest(
                flight_number=payload.flight_number,
                origin=payload.origin.upper(),
                destination=payload.destination.upper(),
                departure_time=_timestamp(payload.departure_time),
                arrival_time=_timestamp(payload.arrival_time),
                total_seats=payload.total_seats,
                price=payload.price,
            ),
            timeout=self.timeout,
        )
        return _flight_to_dict(response.flight)

    def search_flights(self, origin: str, destination: str) -> list[dict]:
        response = self.stub.SearchFlights(
            flight_pb2.SearchFlightsRequest(
                origin=origin.upper(), destination=destination.upper()
            ),
            timeout=self.timeout,
        )
        return [_flight_to_dict(flight) for flight in response.flights]

    def get_flight(self, flight_id: UUID) -> dict:
        response = self.stub.GetFlight(
            flight_pb2.GetFlightRequest(flight_id=str(flight_id)), timeout=self.timeout
        )
        return _flight_to_dict(response.flight)

    def reserve_seats(self, flight_id: UUID, booking_id: UUID, seat_count: int) -> None:
        self.stub.ReserveSeats(
            flight_pb2.ReserveSeatsRequest(
                flight_id=str(flight_id),
                booking_id=str(booking_id),
                seat_count=seat_count,
            ),
            timeout=self.timeout,
        )

    def release_reservation(self, booking_id: UUID) -> None:
        self.stub.ReleaseReservation(
            flight_pb2.ReleaseReservationRequest(booking_id=str(booking_id)),
            timeout=self.timeout,
        )


def _timestamp(value: datetime) -> Timestamp:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    timestamp = Timestamp()
    timestamp.FromDatetime(value.astimezone(timezone.utc))
    return timestamp


def _flight_to_dict(flight) -> dict:
    return {
        "id": flight.id,
        "flight_number": flight.flight_number,
        "origin": flight.origin,
        "destination": flight.destination,
        "departure_time": flight.departure_time.ToDatetime(tzinfo=timezone.utc),
        "arrival_time": flight.arrival_time.ToDatetime(tzinfo=timezone.utc),
        "total_seats": flight.total_seats,
        "available_seats": flight.available_seats,
        "price": flight.price,
        "status": flight_pb2.FlightStatus.Name(flight.status),
    }
