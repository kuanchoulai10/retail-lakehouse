# Jaeger for Thanos

Deploys a Jaeger-compatible distributed tracing collector into the `thanos` namespace using an OpenTelemetryCollector resource. The collector receives traces over OTLP and stores them in memory, making them queryable through the Jaeger UI.

## Deployed Resources

```
Namespace: thanos
└── jaeger-thanos-collector              (Deployment, managed by OTel Operator)
```

## Namespaces

- `thanos` (created by this component's install.sh)

## Pods

| Pod | Purpose |
|-----|---------|
| `jaeger-thanos-collector` | Receives OTLP traces and serves the Jaeger query UI |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `jaeger-thanos-collector` | 16686 (Jaeger UI), 4317 (OTLP gRPC), 4318 (OTLP HTTP) | Primary collector endpoint |
| `jaeger-thanos-collector-extension` | 16686 | Jaeger query UI extension |
| `jaeger-thanos-collector-headless` | 16686, 4317, 4318 | Headless service for direct pod access |
| `jaeger-thanos-collector-monitoring` | 8888 | Collector metrics endpoint |
