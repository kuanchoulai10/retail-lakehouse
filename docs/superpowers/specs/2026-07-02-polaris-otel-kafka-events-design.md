# Polaris Table Commit Events via OTEL Collector to Kafka

## Context

Apache Polaris 1.5.0 introduces a pluggable event listener SPI with a built-in
`opentelemetry` listener that emits catalog events as OTEL log records. This
spec defines how to route those events, filtered to Iceberg table commits
only, through a dedicated OpenTelemetry Collector to a Kafka topic, keyed by
the fully-qualified table identifier so that downstream consumers can process
events per-table in commit order.

The current deployment runs Polaris `1.3.0-incubating`, which pre-dates the
event listener SPI. Upgrading Polaris is a prerequisite. The
opentelemetry-operator is already installed (wave 11) and the Strimzi Kafka
cluster is already running (wave 20), but no `OpenTelemetryCollector` custom
resource has been created yet.

## Goals

- Emit a Kafka message on every successful Iceberg table commit tracked by
  Polaris.
- Use the fully-qualified table identifier as the Kafka message key, so
  events for the same table land on the same partition and remain ordered.
- Keep the pipeline extensible: adding new event types or additional Kafka
  topics later must not require redeploying Polaris.
- Wire the new component into `tasks/apps.yml` so `task onboard` deploys the
  full chain end-to-end.

## Non-Goals

- Consuming the new Kafka topic. Downstream integrations (backend service,
  Trino stream table, etc.) are out of scope.
- Multi-tenant / multi-realm event routing. The current deployment has a
  single realm `POLARIS` and a single catalog `iceberg`; the pipeline is
  scoped accordingly.
- Delivery guarantees beyond OTEL Collector's default retry. Events are
  best-effort telemetry: a Collector restart may drop in-flight batches.
- High-availability partitioning. The topic starts with a single partition,
  matching the current single-broker Kafka cluster.
- Migration of existing Polaris data across the version bump. The upgrade
  from `1.3.0-incubating` to `1.5.0` is expected to be a schema-compatible
  in-place upgrade; if it is not, the fallback is a fresh
  `polaris-bootstrap` run against the same PostgreSQL instance.

## Deployment Topology

```
wave 10: 10-cert-manager
wave 11: 11-otel-operator
wave 20: 20-kafka-cluster
        20-polaris-db
wave 21: 21-polaris (upgraded to 1.5.0, OTEL SDK enabled)
wave 22: 22-polaris-events (new)
         22-kafka-iceberg-connector
wave 23: 23-trino
```

The new component sits in wave 22, deployed after Polaris is ready and after
the Kafka cluster is available. It creates two resources: an
`OpenTelemetryCollector` in namespace `polaris`, and a `KafkaTopic` in
namespace `kafka-cdc`.

## Component: `21-polaris/` changes

### Version bump

`values.yaml`: `polaris.image.tag: "1.5.0"`. The chart repo tag pinned in
`Chart.lock` must be bumped in lockstep. `bootstrap.sh` gets
`POLARIS_VERSION="${POLARIS_VERSION:-1.5.0}"`.

### OTEL SDK activation

Polaris runs on Quarkus, so the OTEL SDK is controlled by Quarkus properties.
These are passed via the Helm chart's `extraEnv` or `configuration` section:

| Property | Value | Purpose |
|---|---|---|
| `quarkus.otel.sdk.disabled` | `false` | Master switch. Off by default. |
| `quarkus.otel.exporter.otlp.endpoint` | `http://polaris-events-collector.polaris.svc.cluster.local:4317` | Where log records go. |
| `quarkus.otel.exporter.otlp.protocol` | `grpc` | Match the collector receiver. |
| `quarkus.otel.logs.exporter` | `otlp` | Enable log export specifically (traces stay off). |

The existing `tracing.enabled: false` stays as-is; this spec only turns on
log export. If traces are desired later, they get a dedicated pipeline in
the collector.

### Event listener configuration

| Property | Value |
|---|---|
| `polaris.event-listener.types` | `opentelemetry` |
| `polaris.event-listener.opentelemetry.enabled-event-types` | `AFTER_UPDATE_TABLE` |

`AFTER_UPDATE_TABLE` fires when an Iceberg REST commit successfully updates
a table's metadata pointer, which is the semantic definition of a
"table write" in Iceberg. Read events (`AFTER_LOAD_TABLE`,
`AFTER_LIST_TABLES`) and lifecycle events (`AFTER_CREATE_TABLE`,
`AFTER_DROP_TABLE`) are intentionally excluded from the MVP; they can be
added by extending this property.

## Component: `22-polaris-events/` (new)

### Files

```
22-polaris-events/
├── README.md
├── otel-collector.yaml       # OpenTelemetryCollector CR in namespace polaris
├── kafka-topic.yaml          # KafkaTopic CR in namespace kafka-cdc
├── bootstrap.sh              # Apply manifests, wait for readiness
└── validate.sh               # Wait deployment ready + topic Ready condition
```

### `OpenTelemetryCollector` CR

- Name: `polaris-events`. The operator creates a matching Service and
  Deployment suffixed with `-collector`, so Polaris addresses it as
  `polaris-events-collector.polaris.svc.cluster.local`.
- Namespace: `polaris`, co-located with Polaris. Keeps the failure domain
  aligned with the app it serves.
- Mode: `deployment`, single replica.
- Image: inherits from the operator's default
  (`otelcol-contrib`), which ships both the `routing` connector and the
  Kafka exporter.

Pipeline shape:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  transform/kafka-key:
    log_statements:
      - context: log
        statements:
          - set(attributes["kafka.key"], attributes["<polaris-table-id-attr>"])
  batch:

exporters:
  kafka/table-commits:
    brokers:
      - kafka-cluster-kafka-bootstrap.kafka-cdc.svc.cluster.local:9092
    topic: polaris.table.commits
    encoding: otlp_json
    message_key_from_metadata_key: kafka.key

service:
  pipelines:
    logs/table-commits:
      receivers: [otlp]
      processors: [transform/kafka-key, batch]
      exporters: [kafka/table-commits]
```

The `<polaris-table-id-attr>` placeholder is the OTEL log-record attribute
that Polaris's `opentelemetry` listener uses to carry the fully-qualified
table identifier. The exact attribute name is not documented in the
configuration reference. The implementation task must inspect a real log
record emitted by Polaris 1.5.0 (either via a temporary `debug` exporter
or by reading the listener source in `runtime/service/src/main/java/org/
apache/polaris/service/events/opentelemetry/`) to fix this value. The
attribute is expected to be a dot-joined string of the form
`<catalog>.<namespace-path>.<table>`.

The `otlp_json` encoding is chosen over the default `otlp_proto` for
downstream debuggability: consumers can `kafka-console-consumer.sh` and
read events as JSON without a proto schema. The trade-off is roughly 2-3x
message size, acceptable at the current expected event rate.

### `KafkaTopic` CR

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: polaris.table.commits
  namespace: kafka-cdc
  labels:
    strimzi.io/cluster: kafka-cluster
spec:
  partitions: 1
  replicas: 1
  config:
    retention.ms: 604800000     # 7 days
    cleanup.policy: delete
```

Single partition matches the single-broker cluster and gives global
ordering across all tables. When the Kafka cluster grows and partitions
are bumped, the message-key routing already ensures per-table ordering is
preserved without any Collector change.

### `bootstrap.sh` / `validate.sh`

Mirror the pattern from `21-polaris/`: idempotent `kubectl apply` with
`--context "${KUBE_CONTEXT}"`, `KUBE_CONTEXT is required` guard,
`log::on_success` / `log::on_failure` from `scripts/utils/log.sh`.

`validate.sh` waits on two conditions:
- `kubectl wait --for=condition=available deployment/polaris-events-collector -n polaris`
- `kubectl wait --for=condition=Ready kafkatopic/polaris.table.commits -n kafka-cdc`

## `tasks/apps.yml` integration

Insert `22-polaris-events/bootstrap.sh` and `22-polaris-events/validate.sh`
into the same list where `22-kafka-iceberg-connector/` is called. Order
within wave 22 does not matter because both new component and the existing
`22-kafka-iceberg-connector` depend only on wave 20 and 21 resources.

## Startup ordering caveats

Polaris starts before the Collector in this wave layout. The Quarkus OTLP
exporter retries on failure and logs a warning; Polaris itself stays
available. Expect a short window (up to a minute during onboard) of
`Failed to export logs` warnings in the Polaris log until the Collector
becomes ready. This is acceptable for a dev cluster.

If this warning noise becomes a problem in future, the fix is to split
`21-polaris/` into a "prepare" step (secrets, DB bootstrap job) and a
"start" step (helm install), and slot the Collector between them.

## Validation

An end-to-end validation walks through:

1. Onboard the cluster with `task onboard KUBE_CONTEXT=retail-lakehouse
   DEPLOY_METHOD=scripts`.
2. Use Spark or Trino (via the deployed Trino instance) to run an
   `INSERT INTO iceberg.<ns>.<table> VALUES (...)` against any Iceberg
   table.
3. Consume `polaris.table.commits` on the Strimzi cluster:
   ```
   kubectl exec -n kafka-cdc kafka-cluster-dual-role-0 -- \
     bin/kafka-console-consumer.sh \
       --bootstrap-server localhost:9092 \
       --topic polaris.table.commits \
       --from-beginning \
       --property print.key=true
   ```
4. Verify each message has the correct fully-qualified table identifier
   as its key and an `otlp_json`-encoded body carrying event metadata.

This validation is captured as a smoke check in `platform/24-e2e-validation/`
if that folder already runs onboard-time E2E checks (to be confirmed
during implementation).

## Open questions for implementation

The following details are deferred to the implementation phase because
they require touching the actual system, not further design discussion:

- The exact OTEL log-record attribute name Polaris uses for the
  fully-qualified table identifier. Placeholder is
  `<polaris-table-id-attr>` in the pipeline config above.
- Whether the Polaris 1.5.0 Helm chart accepts the event-listener
  properties via `configuration:` (structured map) or requires
  `extraEnv:` with `POLARIS_*` environment variables. This affects only
  where in `values.yaml` the properties land, not the properties
  themselves.
- Whether the current PostgreSQL schema for Polaris `1.3.0-incubating`
  requires a migration when moving to `1.5.0`. If the
  `polaris-bootstrap` job fails on second run against the existing DB,
  the fallback is to drop and recreate the Polaris schema (all catalog
  state is dev-only).
