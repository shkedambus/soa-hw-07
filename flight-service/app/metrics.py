from time import perf_counter

import grpc
from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response


SERVICE = "flight-service"
REQUESTS = Counter(
    "grpc_requests_total",
    "Processed gRPC requests.",
    ("service", "method", "endpoint", "status"),
)
ERRORS = Counter(
    "grpc_request_errors_total",
    "Failed gRPC requests.",
    ("service", "method", "endpoint", "error_type"),
)
DURATION = Histogram(
    "grpc_request_duration_seconds",
    "gRPC request duration.",
    ("service", "method", "endpoint"),
)

monitoring_app = FastAPI(title="Flight Service Monitoring")


@monitoring_app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@monitoring_app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class GrpcMetricsInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        handler = continuation(handler_call_details)
        if handler is None or handler.unary_unary is None:
            return handler

        endpoint = handler_call_details.method.rsplit("/", maxsplit=1)[-1]

        def instrumented(request, context):
            started_at = perf_counter()
            status = grpc.StatusCode.OK
            try:
                return handler.unary_unary(request, context)
            finally:
                status = context.code() or status
                status_name = status.name
                REQUESTS.labels(SERVICE, "gRPC", endpoint, status_name).inc()
                DURATION.labels(SERVICE, "gRPC", endpoint).observe(
                    perf_counter() - started_at
                )
                if status != grpc.StatusCode.OK:
                    ERRORS.labels(SERVICE, "gRPC", endpoint, status_name).inc()

        return grpc.unary_unary_rpc_method_handler(
            instrumented,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
