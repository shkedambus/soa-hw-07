# HW-07: CI/CD, Testing & Observability

## Выбор системы

За основу выбрал систему Flight Booking из `hw-03`.

Оба сервиса написаны на Python. Межсервисный контракт описан в
`proto/flight.proto` и генерируется в Docker build через `grpc_tools.protoc`.
Каждая база принадлежит одному сервису, миграции выполняет Flyway при старте.

## Доменный сценарий

Публичным API является `booking-service`:

| Endpoint | Назначение |
|---|---|
| `POST /flights` | Создать рейс через gRPC-вызов Flight Service |
| `GET /flights?origin=SVO&destination=LED` | Найти доступные рейсы |
| `GET /flights/{id}` | Получить текущие свободные места |
| `POST /bookings` | Получить рейс, атомарно зарезервировать места и сохранить бронь |
| `POST /bookings/{id}/cancel` | Освободить места и отменить бронь |
| `GET /health`, `GET /metrics` | Health и Prometheus metrics |

`flight-service` владеет таблицами `flights` и `seat_reservations`.
`ReserveSeats` блокирует строку рейса через `SELECT FOR UPDATE`, уменьшает
`available_seats` и создает резервацию в одной транзакции. `booking-service`
сохраняет рассчитанный snapshot стоимости в своей таблице `bookings`.

## Запуск

Весь стек запускается одной командой:

```bash
cd hw-07
docker compose up --build
```

Для запуска в фоне с ожиданием health checks:

```bash
make up
```

После старта доступны:

| Компонент | URL |
|---|---|
| Booking API / Swagger | http://localhost:8080/docs |
| Booking metrics | http://localhost:8080/metrics |
| Flight metrics | http://localhost:8081/metrics |
| Prometheus | http://localhost:9090 |
| Alertmanager | http://localhost:9093 |
| Grafana (`admin` / `admin`) | http://localhost:3000 |

## Тестирование

Команды запускаются из `hw-07`:

```bash
make up
make unit
make integration
make e2e
make load
make verify-alert
```

| Проверка | Что доказывает |
|---|---|
| Unit tests | Расчет стоимости и доменные ограничения рейса/мест |
| Integration tests | REST-запрос вызывает gRPC-сервис; успешная бронь сохраняется в `bookings` и `seat_reservations`; превышение оставшихся мест возвращает `409` без лишней брони; неизвестный рейс возвращает `404` без записи в `bookings` |
| E2E tests | Создание рейса -> бронирование -> уменьшение мест -> отмена -> восстановление мест; повторная отмена возвращает `409` и не освобождает места второй раз |
| Load test | `Locust`, 10 пользователей, 30 секунд поиска рейсов, с fail thresholds |
| SLI verification | Числовые условия читаются из Prometheus API, а не hardcode-результата |
| Alert verification | Поток запросов отсутствующего рейса приводит `BookingHighErrorRate` в `firing` |

Integration и E2E используют уникальные рейсы и в `finally` удаляют созданные
брони, резервации и рейсы, поэтому не зависят от порядка запусков.

## Метрики и dashboard

`booking-service` инструментирован через FastAPI middleware:

| Metric | Labels |
|---|---|
| `http_requests_total` | `service`, `method`, `endpoint`, `status` |
| `http_request_errors_total` | `service`, `method`, `endpoint`, `error_type` |
| `http_request_duration_seconds` | `service`, `method`, `endpoint` |

`flight-service` инструментирован gRPC server interceptor и экспортирует аналогичные
метрики через свой HTTP `/metrics`:

| Metric | Labels |
|---|---|
| `grpc_requests_total` | `service`, `method`, `endpoint`, `status` |
| `grpc_request_errors_total` | `service`, `method`, `endpoint`, `error_type` |
| `grpc_request_duration_seconds` | `service`, `method`, `endpoint` |

Prometheus также собирает метрики двух PostgreSQL через `postgres-exporter`.
Grafana provisioning загружает автоматически:

| Dashboard | Панели |
|---|---|
| `Flight Booking Services` | Отдельные секции Booking и Flight: throughput, p50/p95/p99 latency, errors, availability - по 4 панели на сервис |
| `Flight Booking Infrastructure` | PostgreSQL availability, connections и committed transactions rate |

JSON dashboard-ов хранится в `infra/grafana/dashboards`.

## Load test и SLI/SLO

Нагрузка идет на поиск рейсов: читающий путь через REST, gRPC и PostgreSQL,
места не расходует.
`load/locustfile.py` завершает прогон ошибкой при `error rate >= 1%` или
`p95 >= 500 ms`. Порог p95 достаточен для локального запроса к двум контейнерам
с одной простой индексированной выборкой; превышение означает деградацию,
видимую пользователю.

System-level SLI после нагрузки проверяет `scripts/verify_sli.py`:

| SLI | PromQL | SLO | Порог отказа CI |
|---|---|---|---|
| API availability | `sum(rate(http_requests_total{service="booking-service",endpoint="/flights",status=~"2.."}[1m])) / sum(rate(http_requests_total{service="booking-service",endpoint="/flights"}[1m]))` | `> 99.5%` | `<= 99%` |
| End-to-end search latency p95 | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service="booking-service",endpoint="/flights"}[1m])) by (le))` | `< 300 ms` | `>= 500 ms` |

Search latency является end-to-end SLI: REST response возвращается только после
завершения gRPC-вызова Flight Service и чтения его PostgreSQL.
Отчет проверки сохраняется в `artifacts/sli_report.json`, а результат Locust -
в `artifacts/load_thresholds.json` и CSV-файлах.

## Alerts as Code

Правила находятся в `infra/prometheus/alerts.yml`, Alertmanager автоматически
поднимается в compose:

| Alert | Условие |
|---|---|
| `BookingServiceDown` | target API недоступен 10 секунд |
| `BookingHighErrorRate` | error rate `GET /flights/{flight_id}` выше 5% |
| `BookingHighLatency` | p95 API выше 1 секунды 10 секунд |

`make verify-alert` выполняет запросы отсутствующего рейса, дожидается
срабатывания `BookingHighErrorRate` через Prometheus API и его появления через
Alertmanager API, затем сохраняет подтверждение в `artifacts/alert_verification.json`.
Сработавший alert виден в UI Prometheus и Alertmanager.

## GitHub Actions CI

Pipeline хранится в `.github/workflows/ci.yml` и запускается при `push` и
`pull_request` средствами GitHub Actions. Этапы:

```text
build -> unit_tests -> integration_tests -> e2e_tests -> load_metrics_and_alerts
```

Финальный job в одном окружении запускает E2E, нагрузку, получает реальные
метрики Prometheus, проверяет SLI и подтверждает firing alert. При ошибке любого
шага job завершается ненулевым кодом. Логи compose и отчеты нагрузки/SLI/alerts
публикуются как artifacts с `if: always()`.

## Демонстрация на защите

```bash
make up
make integration
make e2e
make load
make verify-alert
```

Затем открыть Grafana, Prometheus targets/alerts и Alertmanager. Записи в базах:

```bash
docker compose exec booking-db psql -U postgres -d booking -c "SELECT * FROM bookings;"
docker compose exec flight-db psql -U postgres -d flight -c "SELECT * FROM seat_reservations;"
```

Остановка с очисткой состояния:

```bash
make down
```
