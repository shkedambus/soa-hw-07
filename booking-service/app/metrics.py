from time import perf_counter

from fastapi import Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response


SERVICE = "booking-service"
REQUESTS = Counter(
    "http_requests_total",
    "Processed HTTP requests.",
    ("service", "method", "endpoint", "status"),
)
ERRORS = Counter(
    "http_request_errors_total",
    "Failed HTTP requests.",
    ("service", "method", "endpoint", "error_type"),
)
DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration.",
    ("service", "method", "endpoint"),
)


async def record_http_metrics(request: Request, call_next):
    started_at = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        endpoint = getattr(route, "path", request.url.path)
        method = request.method
        REQUESTS.labels(SERVICE, method, endpoint, str(status_code)).inc()
        DURATION.labels(SERVICE, method, endpoint).observe(perf_counter() - started_at)
        if status_code >= 400:
            ERRORS.labels(SERVICE, method, endpoint, str(status_code)).inc()


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
