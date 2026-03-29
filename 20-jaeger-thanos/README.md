# Jaeger for Thanos

Deploys a Jaeger-compatible distributed tracing collector into the `thanos` namespace using an OpenTelemetryCollector resource. The collector receives traces over OTLP and stores them in memory, making them queryable through the Jaeger UI.

## Deployed Resources

```
Namespace: thanos
└── jaeger-thanos-collector              (Deployment, managed by OTel Operator)
```

## Namespaces

- `thanos` (pre-existing, created by `30-thanos`)

## Pods

| Pod | Purpose |
|-----|---------|
| `jaeger-thanos-collector` | Receives OTLP traces and serves the Jaeger query UI |
