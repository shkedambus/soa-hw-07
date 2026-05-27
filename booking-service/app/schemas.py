from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BookingStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class CreateFlightRequest(BaseModel):
    flight_number: str = Field(min_length=2, max_length=16)
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    departure_time: datetime
    arrival_time: datetime
    total_seats: int = Field(gt=0)
    price: float = Field(gt=0)


class FlightResponse(BaseModel):
    id: UUID
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    total_seats: int
    available_seats: int
    price: float
    status: str


class CreateBookingRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    flight_id: UUID
    passenger_name: str = Field(min_length=1, max_length=255)
    passenger_email: str = Field(min_length=3, max_length=255)
    seat_count: int = Field(gt=0)


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    flight_id: UUID
    passenger_name: str
    passenger_email: str
    seat_count: int
    total_price: float
    status: BookingStatus
    created_at: datetime
    updated_at: datetime
