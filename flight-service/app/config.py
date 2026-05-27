import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@flight-db:5432/flight",
    )
    grpc_bind: str = os.getenv("GRPC_BIND", "0.0.0.0:50051")
    metrics_port: int = int(os.getenv("METRICS_PORT", "8081"))
    grpc_workers: int = int(os.getenv("GRPC_WORKERS", "12"))


settings = Settings()
