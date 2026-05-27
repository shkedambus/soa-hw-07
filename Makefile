.PHONY: build up down unit integration e2e load verify-alert test

build:
	docker compose build

up:
	docker compose up -d --build --wait

down:
	docker compose --profile tests down -v --remove-orphans

unit:
	docker compose run --rm --no-deps booking-service pytest -q tests/unit
	docker compose run --rm --no-deps flight-service pytest -q tests/unit

integration:
	docker compose --profile tests build test-runner
	docker compose --profile tests run --rm test-runner pytest -q tests/integration

e2e:
	docker compose --profile tests build test-runner
	docker compose --profile tests run --rm test-runner pytest -q tests/e2e

load:
	docker compose --profile tests build load-test test-runner
	docker compose --profile tests run --rm load-test
	docker compose --profile tests run --rm test-runner python scripts/verify_sli.py

verify-alert:
	docker compose --profile tests build test-runner
	docker compose --profile tests run --rm test-runner python scripts/verify_alert.py

test: unit integration e2e load verify-alert
