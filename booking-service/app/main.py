import logging
import uuid
from datetime import datetime, timezone
from typing import Generator

import grpc
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.domain import calculate_total_price
from app.grpc_client import FlightClient
from app.metrics import metrics_response, record_http_metrics
from app.models import Booking
from app.schemas import (
    BookingResponse,
    BookingStatus,
    CreateBookingRequest,
    CreateFlightRequest,
    FlightResponse,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = FastAPI(title="Flight Booking API", version="1.0.0")
app.middleware("http")(record_http_metrics)
flight_client = FlightClient()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def grpc_http_error(error: grpc.RpcError) -> HTTPException:
    status_by_code = {
        grpc.StatusCode.INVALID_ARGUMENT: 400,
        grpc.StatusCode.NOT_FOUND: 404,
        grpc.StatusCode.ALREADY_EXISTS: 409,
        grpc.StatusCode.FAILED_PRECONDITION: 409,
        grpc.StatusCode.RESOURCE_EXHAUSTED: 409,
        grpc.StatusCode.UNAVAILABLE: 503,
        grpc.StatusCode.DEADLINE_EXCEEDED: 503,
    }
    return HTTPException(
        status_code=status_by_code.get(error.code(), 502),
        detail=error.details() or "flight service request failed",
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return metrics_response()


@app.post("/flights", response_model=FlightResponse, status_code=201)
def create_flight(payload: CreateFlightRequest):
    try:
        return flight_client.create_flight(payload)
    except grpc.RpcError as error:
        raise grpc_http_error(error) from error


@app.get("/flights", response_model=list[FlightResponse])
def search_flights(
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
):
    try:
        return flight_client.search_flights(origin, destination)
    except grpc.RpcError as error:
        raise grpc_http_error(error) from error


@app.get("/flights/{flight_id}", response_model=FlightResponse)
def get_flight(flight_id: uuid.UUID):
    try:
        return flight_client.get_flight(flight_id)
    except grpc.RpcError as error:
        raise grpc_http_error(error) from error


@app.post("/bookings", response_model=BookingResponse, status_code=201)
def create_booking(payload: CreateBookingRequest, db: Session = Depends(get_db)):
    booking_id = uuid.uuid4()
    try:
        flight = flight_client.get_flight(payload.flight_id)
        flight_client.reserve_seats(payload.flight_id, booking_id, payload.seat_count)
    except grpc.RpcError as error:
        raise grpc_http_error(error) from error

    booking = Booking(
        id=booking_id,
        user_id=payload.user_id,
        flight_id=payload.flight_id,
        passenger_name=payload.passenger_name,
        passenger_email=payload.passenger_email,
        seat_count=payload.seat_count,
        total_price=calculate_total_price(flight["price"], payload.seat_count),
        status=BookingStatus.CONFIRMED.value,
    )
    try:
        db.add(booking)
        db.commit()
        db.refresh(booking)
    except Exception:
        db.rollback()
        try:
            flight_client.release_reservation(booking_id)
        except grpc.RpcError:
            logging.exception("Failed to compensate reservation %s", booking_id)
        raise
    return booking


@app.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: uuid.UUID, db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    return booking


@app.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(booking_id: uuid.UUID, db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    if booking.status != BookingStatus.CONFIRMED.value:
        raise HTTPException(status_code=409, detail="booking is already cancelled")
    try:
        flight_client.release_reservation(booking_id)
    except grpc.RpcError as error:
        raise grpc_http_error(error) from error
    booking.status = BookingStatus.CANCELLED.value
    booking.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(booking)
    return booking
