import logging
from concurrent import futures
from threading import Thread

import flight_pb2_grpc
import grpc
import uvicorn

from app.config import settings
from app.metrics import GrpcMetricsInterceptor, monitoring_app
from app.service import FlightService


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def serve() -> None:
    Thread(
        target=uvicorn.run,
        kwargs={
            "app": monitoring_app,
            "host": "0.0.0.0",
            "port": settings.metrics_port,
            "log_level": "info",
        },
        daemon=True,
    ).start()
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=settings.grpc_workers),
        interceptors=[GrpcMetricsInterceptor()],
    )
    flight_pb2_grpc.add_FlightServiceServicer_to_server(FlightService(), server)
    server.add_insecure_port(settings.grpc_bind)
    server.start()
    logging.info("Flight gRPC service listening on %s", settings.grpc_bind)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
