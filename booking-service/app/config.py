import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@booking-db:5432/booking",
    )
    flight_grpc_target: str = os.getenv("FLIGHT_GRPC_TARGET", "flight-service:50051")
    grpc_timeout_seconds: float = float(os.getenv("GRPC_TIMEOUT_SECONDS", "3"))


settings = Settings()
