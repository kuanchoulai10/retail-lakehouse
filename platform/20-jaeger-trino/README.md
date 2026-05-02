# Jaeger for Trino

Deploys a Jaeger-compatible distributed tracing collector into the `trino` namespace using an OpenTelemetryCollector resource. The collector receives traces over OTLP and stores them in memory, making them queryable through the Jaeger UI.

## Deployed Resources

```
Namespace: trino
└── jaeger-collector                     (Deployment, managed by OTel Operator)
```

## Namespaces

- `trino` (created by this component's install.sh)

## Pods

| Pod | Purpose |
|-----|---------|
| `jaeger-collector` | Receives OTLP traces and serves the Jaeger query UI |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `jaeger-collector` | 16686 (Jaeger UI), 4317 (OTLP gRPC), 4318 (OTLP HTTP) | Primary collector endpoint |
| `jaeger-collector-extension` | 16686 | Jaeger query UI extension |
| `jaeger-collector-headless` | 16686, 4317, 4318 | Headless service for direct pod access |
| `jaeger-collector-monitoring` | 8888 | Collector metrics endpoint |
