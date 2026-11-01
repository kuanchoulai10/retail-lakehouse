# Jaeger for Trino

Deploys a Jaeger-compatible distributed tracing collector into the `lakehouse-query-engine` namespace using an OpenTelemetryCollector resource. The collector receives traces over OTLP and stores them in memory, making them queryable through the Jaeger UI.

## Deployed Resources

```
Namespace: lakehouse-query-engine
└── jaeger-collector                     (Deployment, managed by OTel Operator)
```

## Namespaces

- `lakehouse-query-engine` (created by this component's install.sh)

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

## Memory

The collector keeps traces in memory (`max_traces: 20000`, was `100000`) with a memory limit of `512Mi` and a request of `256Mi` (it used 157 MiB after a 30 minute soak). The request is sized from usage, not set equal to the limit: with request = limit on Kafka, both KafkaConnects, RustFS and Jaeger the node had 27013Mi of 28005Mi allocatable requested, and Spark maintenance executors (1433Mi each) could not be scheduled. It used about 520 MiB before the change (long-running, 100000 traces) and about 100 MiB after the restart; the 512Mi limit is the brief value, kept as headroom while the in-memory store refills.
