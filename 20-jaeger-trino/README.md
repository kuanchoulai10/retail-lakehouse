# Jaeger for Trino

Deploys a Jaeger-compatible distributed tracing collector into the `trino` namespace using an OpenTelemetryCollector resource. The collector receives traces over OTLP and stores them in memory, making them queryable through the Jaeger UI.

## Deployed Resources

```
Namespace: trino
└── jaeger-collector                     (Deployment, managed by OTel Operator)
```

## Namespaces

- `trino` (pre-existing, created by `23-trino`)

## Pods

| Pod | Purpose |
|-----|---------|
| `jaeger-collector` | Receives OTLP traces and serves the Jaeger query UI |
