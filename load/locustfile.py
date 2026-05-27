import json
from pathlib import Path

from locust import HttpUser, between, events, task


MAX_ERROR_RATE = 0.01
MAX_P95_MS = 500


class Passenger(HttpUser):
    wait_time = between(0.05, 0.2)

    @task
    def search_available_flights(self) -> None:
        self.client.get(
            "/flights?origin=SVO&destination=LED",
            name="GET /flights search",
        )


@events.quitting.add_listener
def enforce_thresholds(environment, **_kwargs) -> None:
    statistics = environment.stats.total
    p95_ms = statistics.get_response_time_percentile(0.95) or 0
    summary = {
        "requests": statistics.num_requests,
        "fail_ratio": statistics.fail_ratio,
        "p95_ms": p95_ms,
        "thresholds": {"max_error_rate": MAX_ERROR_RATE, "max_p95_ms": MAX_P95_MS},
    }
    Path("/artifacts/load_thresholds.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    if statistics.fail_ratio >= MAX_ERROR_RATE or p95_ms >= MAX_P95_MS:
        environment.process_exit_code = 1
