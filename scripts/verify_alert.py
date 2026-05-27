import json
import os
import time
from pathlib import Path

import requests


API_URL = os.getenv("API_URL", "http://booking-service:8080")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
ALERTMANAGER_URL = os.getenv("ALERTMANAGER_URL", "http://alertmanager:9093")
MISSING_FLIGHT_ID = "00000000-0000-0000-0000-000000000404"


def alert_is_firing() -> bool:
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/alerts", timeout=5)
    response.raise_for_status()
    alerts = response.json()["data"]["alerts"]
    return any(
        item["labels"].get("alertname") == "BookingHighErrorRate"
        and item["state"] == "firing"
        for item in alerts
    )


def alertmanager_contains_alert() -> bool:
    response = requests.get(f"{ALERTMANAGER_URL}/api/v2/alerts", timeout=5)
    response.raise_for_status()
    return any(
        item["labels"].get("alertname") == "BookingHighErrorRate"
        for item in response.json()
    )


def send_expected_failures() -> int:
    failures = 0
    end_at = time.monotonic() + 1
    while time.monotonic() < end_at:
        response = requests.get(f"{API_URL}/flights/{MISSING_FLIGHT_ID}", timeout=5)
        if response.status_code != 404:
            raise SystemExit(f"Expected 404, received {response.status_code}")
        failures += 1
    return failures


def main() -> None:
    failures = 0
    for _ in range(15):
        failures += send_expected_failures()
        if alert_is_firing() and alertmanager_contains_alert():
            result = {
                "alert": "BookingHighErrorRate",
                "prometheus_state": "firing",
                "alertmanager_visible": True,
                "requests": failures,
            }
            Path("/artifacts/alert_verification.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            print(json.dumps(result, indent=2))
            return
        time.sleep(2)
    raise SystemExit("BookingHighErrorRate was not firing and visible in Alertmanager")


if __name__ == "__main__":
    main()
