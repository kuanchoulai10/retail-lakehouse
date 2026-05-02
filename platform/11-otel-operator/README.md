# OpenTelemetry Operator

Deploys the OpenTelemetry Operator via Helm. The operator manages the lifecycle of OpenTelemetry Collector instances and auto-instrumentation resources. In this stack, it is used to deploy Jaeger-compatible collectors for distributed tracing in the Thanos and Trino namespaces.

## Deployed Resources

```
Namespace: opentelemetry-operator
└── opentelemetry-operator   (Deployment)
```

## Namespaces

- `opentelemetry-operator`

## Pods

| Pod | Purpose |
|-----|---------|
| `opentelemetry-operator` | Reconciles OpenTelemetryCollector and Instrumentation resources |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `opentelemetry-operator` | 8443, 8080 | Operator metrics and health endpoint |
| `opentelemetry-operator-webhook` | 443 | Admission webhook for OpenTelemetryCollector validation |

## CRDs

| CRD | Purpose |
|-----|---------|
| `opentelemetrycollectors.opentelemetry.io` | Declares an OpenTelemetry Collector deployment |
| `instrumentations.opentelemetry.io` | Configures auto-instrumentation injection into application pods |
| `opampbridges.opentelemetry.io` | Manages Collector configuration via the OpAMP protocol |
| `targetallocators.opentelemetry.io` | Distributes Prometheus scrape targets across Collector replicas |
