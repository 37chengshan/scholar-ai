# ScholarAI API Service Level Objectives (SLO)

> Phase 5.0-7 deliverable: Observability SLO baseline

## SLO Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Latency P95 | < 500ms | `http_request_duration_seconds` histogram, 95th percentile |
| Error Rate | < 1% | `http_requests_total{status=~"5.."}` / `http_requests_total` |
| Availability | > 99.5% | Uptime of `/health/deps` returning `"status": "healthy"` |

## Metrics

### Exposed Endpoints

- `/metrics` -- Prometheus-format metrics (no auth required)
- `/health/deps` -- Dependency health check (PG, Redis, Neo4j)
- `/health` -- Full health check including AI service status

### Prometheus Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | method, status, endpoint | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | method, endpoint | Request duration |

### Histogram Buckets

```
0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0 seconds
```

## Alerting Rules

### Slow Request Warning

Requests exceeding 2000ms trigger a `slow_request` warning log.

```yaml
# Example Prometheus alert (deployment-time)
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "API P95 latency exceeds 500ms SLO"

- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "API error rate exceeds 1% SLO"
```

## Dependency Health

`/health/deps` checks:

| Dependency | Check | Healthy When |
|------------|-------|--------------|
| PostgreSQL | `SELECT 1` | Query succeeds |
| Redis | `PING` | Pong received |
| Neo4j | `RETURN 1` | Query succeeds |

Returns `{"status": "healthy", "dependencies": {...}}` or `{"status": "degraded", ...}`.

## Middleware Observability

- Single `ObservabilityMiddleware` handles: request logging, trace_id binding, slow request warnings
- Health endpoints (`/health`, `/health/`) are excluded from request logs to reduce noise
- Each request produces exactly one `request_started` + one `request_completed` log (except health)
