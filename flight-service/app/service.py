import uuid
from datetime import datetime, timezone
from decimal import Decimal

import flight_pb2
import flight_pb2_grpc
import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from sqlalchemy import select

from app.database import SessionLocal
from app.domain import ensure_seats_available, validate_new_flight
from app.models import Flight, SeatReservation


class FlightService(flight_pb2_grpc.FlightServiceServicer):
    def CreateFlight(self, request, context):
        departure_time = request.departure_time.ToDatetime(tzinfo=timezone.utc)
        arrival_time = request.arrival_time.ToDatetime(tzinfo=timezone.utc)
        origin = request.origin.upper()
        destination = request.destination.upper()
        try:
            validate_new_flight(
                origin,
                destination,
                departure_time,
                arrival_time,
                request.total_seats,
                request.price,
            )
        except ValueError as error:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(error))

        flight = Flight(
            id=uuid.uuid4(),
            flight_number=request.flight_number.upper(),
            origin=origin,
            destination=destination,
            departure_time=departure_time,
            arrival_time=arrival_time,
            total_seats=request.total_seats,
            available_seats=request.total_seats,
            price=Decimal(str(request.price)),
            status="SCHEDULED",
        )
        try:
            with SessionLocal() as session:
                session.add(flight)
                session.commit()
                session.refresh(flight)
        except Exception:
            context.abort(grpc.StatusCode.ALREADY_EXISTS, "flight number already exists")
        return flight_pb2.FlightResponse(flight=_flight_to_proto(flight))

    def SearchFlights(self, request, context):
        with SessionLocal() as session:
            flights = session.execute(
                select(Flight)
                .where(
                    Flight.origin == request.origin.upper(),
                    Flight.destination == request.destination.upper(),
                    Flight.status == "SCHEDULED",
                )
                .order_by(Flight.departure_time)
            ).scalars()
            return flight_pb2.SearchFlightsResponse(
                flights=[_flight_to_proto(flight) for flight in flights]
            )

    def GetFlight(self, request, context):
        flight_id = _uuid(request.flight_id, context)
        with SessionLocal() as session:
            flight = session.get(Flight, flight_id)
            if flight is None:
                context.abort(grpc.StatusCode.NOT_FOUND, "flight not found")
            return flight_pb2.FlightResponse(flight=_flight_to_proto(flight))

    def ReserveSeats(self, request, context):
        flight_id = _uuid(request.flight_id, context)
        booking_id = _uuid(request.booking_id, context)
        with SessionLocal() as session:
            with session.begin():
                previous = session.execute(
                    select(SeatReservation).where(SeatReservation.booking_id == booking_id)
                ).scalar_one_or_none()
                if previous is not None:
                    return flight_pb2.ReservationResponse(
                        reservation=_reservation_to_proto(previous)
                    )
                flight = session.execute(
                    select(Flight).where(Flight.id == flight_id).with_for_update()
                ).scalar_one_or_none()
                if flight is None:
                    context.abort(grpc.StatusCode.NOT_FOUND, "flight not found")
                try:
                    ensure_seats_available(flight.available_seats, request.seat_count)
                except ValueError as error:
                    context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(error))
                except LookupError as error:
                    context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, str(error))
                flight.available_seats -= request.seat_count
                flight.updated_at = datetime.now(timezone.utc)
                reservation = SeatReservation(
                    id=uuid.uuid4(),
                    booking_id=booking_id,
                    flight_id=flight_id,
                    seat_count=request.seat_count,
                    status="ACTIVE",
                )
                session.add(reservation)
            session.refresh(reservation)
            return flight_pb2.ReservationResponse(
                reservation=_reservation_to_proto(reservation)
            )

    def ReleaseReservation(self, request, context):
        booking_id = _uuid(request.booking_id, context)
        with SessionLocal() as session:
            with session.begin():
                reservation = session.execute(
                    select(SeatReservation)
                    .where(SeatReservation.booking_id == booking_id)
                    .with_for_update()
                ).scalar_one_or_none()
                if reservation is None:
                    context.abort(grpc.StatusCode.NOT_FOUND, "reservation not found")
                if reservation.status == "ACTIVE":
                    flight = session.execute(
                        select(Flight)
                        .where(Flight.id == reservation.flight_id)
                        .with_for_update()
                    ).scalar_one()
                    flight.available_seats += reservation.seat_count
                    flight.updated_at = datetime.now(timezone.utc)
                    reservation.status = "RELEASED"
                    reservation.updated_at = datetime.now(timezone.utc)
            session.refresh(reservation)
            return flight_pb2.ReservationResponse(
                reservation=_reservation_to_proto(reservation)
            )


def _uuid(value: str, context) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        context.abort(grpc.StatusCode.INVALID_ARGUMENT, "invalid UUID")


def _timestamp(value: datetime) -> Timestamp:
    timestamp = Timestamp()
    timestamp.FromDatetime(value.astimezone(timezone.utc))
    return timestamp


def _flight_to_proto(flight: Flight) -> flight_pb2.Flight:
    return flight_pb2.Flight(
        id=str(flight.id),
        flight_number=flight.flight_number,
        origin=flight.origin,
        destination=flight.destination,
        departure_time=_timestamp(flight.departure_time),
        arrival_time=_timestamp(flight.arrival_time),
        total_seats=flight.total_seats,
        available_seats=flight.available_seats,
        price=float(flight.price),
        status=flight_pb2.SCHEDULED,
    )


def _reservation_to_proto(reservation: SeatReservation) -> flight_pb2.Reservation:
    status = (
        flight_pb2.ACTIVE if reservation.status == "ACTIVE" else flight_pb2.RELEASED
    )
    return flight_pb2.Reservation(
        id=str(reservation.id),
        booking_id=str(reservation.booking_id),
        flight_id=str(reservation.flight_id),
        seat_count=reservation.seat_count,
        status=status,
    )
