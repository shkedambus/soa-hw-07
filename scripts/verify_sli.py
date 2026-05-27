import json
import os
import time
from pathlib import Path

import requests


PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
MAX_P95_SECONDS = 0.5
MIN_AVAILABILITY = 0.99
QUERIES = {
    "api_latency_p95_seconds": """
        histogram_quantile(0.95,
          sum(rate(http_request_duration_seconds_bucket{
            service="booking-service",endpoint="/flights"
          }[1m])) by (le)
        )
    """,
    "api_availability": """
        sum(rate(http_requests_total{
          service="booking-service",endpoint="/flights",status=~"2.."
        }[1m]))
        /
        sum(rate(http_requests_total{
          service="booking-service",endpoint="/flights"
        }[1m]))
    """,
}


def query(expression: str) -> float | None:
    response = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query", params={"query": expression}, timeout=5
    )
    response.raise_for_status()
    result = response.json()["data"]["result"]
    if not result:
        return None
    raw_value = result[0]["value"][1]
    if raw_value in {"NaN", "+Inf", "-Inf"}:
        return None
    return float(raw_value)


def collect_sli() -> dict[str, float]:
    for _ in range(15):
        values = {name: query(expression) for name, expression in QUERIES.items()}
        if all(value is not None for value in values.values()):
            return values  # type: ignore[return-value]
        time.sleep(2)
    raise RuntimeError("Prometheus did not return SLI data after load")


def main() -> None:
    health = requests.get("http://booking-service:8080/health", timeout=5)
    health.raise_for_status()
    values = collect_sli()
    report = {
        "values": values,
        "failure_thresholds": {
            "api_latency_p95_seconds": MAX_P95_SECONDS,
            "api_availability": MIN_AVAILABILITY,
        },
    }
    Path("/artifacts/sli_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    if values["api_latency_p95_seconds"] >= MAX_P95_SECONDS:
        raise SystemExit(f"p95 latency failed: {values['api_latency_p95_seconds']}")
    if values["api_availability"] <= MIN_AVAILABILITY:
        raise SystemExit(f"availability failed: {values['api_availability']}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
