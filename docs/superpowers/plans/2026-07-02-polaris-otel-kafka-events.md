# Polaris Table Commit Events via OTEL to Kafka Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route Polaris table commit events (`AFTER_UPDATE_TABLE`) through a new OpenTelemetry Collector to a Kafka topic `polaris.table.commits`, keyed by the fully-qualified table identifier, wired into `task onboard`.

**Architecture:** Upgrade `platform/21-polaris/` from `1.3.0-incubating` to `1.5.0` and turn on the built-in `opentelemetry` event listener. Add a new wave-22 component `platform/22-polaris-events/` that provisions an `OpenTelemetryCollector` CR (OTLP receiver, OTTL transform for the message key, batch, Kafka exporter) plus a Strimzi `KafkaTopic` CR.

**Tech Stack:** Apache Polaris 1.5.0 (Quarkus), OpenTelemetry Collector (contrib image, deployed via `opentelemetry-operator`), Strimzi Kafka, kubectl / helm, Taskfile.

**Spec reference:** `docs/superpowers/specs/2026-07-02-polaris-otel-kafka-events-design.md`

---

## File Structure

```
platform/21-polaris/
├── Chart.yaml                (modify: bump polaris subchart 1.3.0-incubating → 1.5.0)
├── Chart.lock                (regenerate via `helm dependency update`)
├── charts/                   (regenerate: contains vendored 1.5.0 subchart tarball)
├── values.yaml               (modify: enable OTEL SDK, event listener, endpoint)
└── bootstrap.sh              (modify: default POLARIS_VERSION="1.5.0")

platform/22-polaris-events/    (new)
├── README.md
├── otel-collector.yaml       (OpenTelemetryCollector CR, name: polaris-events)
├── kafka-topic.yaml          (KafkaTopic CR: polaris.table.commits)
├── bootstrap.sh              (kubectl apply both CRs)
└── validate.sh               (wait deployment + KafkaTopic Ready)

tasks/apps.yml                (modify: add 22-polaris-events into bootstrap-by-scripts
                                       + validate deps + validate-polaris-events task)
```

Each file has a single responsibility. The two CRs live in separate files because
they target different namespaces (`polaris` vs `kafka-cdc`) and different operators
(otel-operator vs Strimzi topic-operator); a future contributor changing one should
not have to open the other.

---

## Task 1: Bump Polaris subchart to 1.5.0

**Files:**
- Modify: `platform/21-polaris/Chart.yaml`
- Regenerate: `platform/21-polaris/Chart.lock`, `platform/21-polaris/charts/`
- Modify: `platform/21-polaris/bootstrap.sh`

- [ ] **Step 1: Edit `Chart.yaml` dependency version**

Change the polaris dependency from `1.3.0-incubating` to `1.5.0`:

```yaml
apiVersion: v2
name: polaris-wrapper
description: Wrapper chart for Apache Polaris Iceberg REST catalog
type: application
version: 0.1.0
dependencies:
  - name: polaris
    version: 1.5.0
    repository: https://downloads.apache.org/incubator/polaris/helm-chart
```

- [ ] **Step 2: Regenerate Chart.lock and vendored subchart**

Run:
```bash
helm dependency update /Users/kcl/Projects/retail-lakehouse/platform/21-polaris/
```

Expected: `Chart.lock` shows `version: 1.5.0`, `charts/` contains `polaris-1.5.0.tgz` (old `polaris-1.3.0-incubating.tgz` is removed).

- [ ] **Step 3: Update default version in bootstrap.sh**

Replace the `POLARIS_VERSION` default in `platform/21-polaris/bootstrap.sh`:

```bash
POLARIS_VERSION="${POLARIS_VERSION:-1.5.0}"
```

- [ ] **Step 4: Sanity-check the new chart renders**

Run:
```bash
helm template polaris /Users/kcl/Projects/retail-lakehouse/platform/21-polaris/ \
  --values /Users/kcl/Projects/retail-lakehouse/platform/21-polaris/values.yaml \
  > /tmp/polaris-render.yaml
```

Expected: exit 0, `/tmp/polaris-render.yaml` contains a `kind: Deployment` for polaris with `image: apache/polaris:1.5.0`. If the render errors on any value key, note which — those keys may have been renamed between 1.3 and 1.5 and Task 2 will need to adapt.

- [ ] **Step 5: Commit**

```bash
git add platform/21-polaris/Chart.yaml platform/21-polaris/Chart.lock platform/21-polaris/charts/ platform/21-polaris/bootstrap.sh
git commit -m "chore(polaris): bump helm subchart 1.3.0-incubating → 1.5.0"
```

---

## Task 2: Enable OTEL SDK and event listener in Polaris values

**Files:**
- Modify: `platform/21-polaris/values.yaml`

- [ ] **Step 1: Turn on OTEL log export and configure endpoint**

Set `polaris.tracing.enabled: true` in `values.yaml` and add the Quarkus OTEL SDK properties. The polaris subchart exposes these under a `configuration:` map. Locate the existing `polaris:` top-level key and add:

```yaml
polaris:
  # ... existing values ...

  tracing:
    enabled: true

  configuration:
    # Quarkus OTEL SDK
    quarkus.otel.sdk.disabled: "false"
    quarkus.otel.exporter.otlp.endpoint: "http://polaris-events-collector.polaris.svc.cluster.local:4317"
    quarkus.otel.exporter.otlp.protocol: "grpc"
    quarkus.otel.logs.exporter: "otlp"
    quarkus.otel.traces.exporter: "none"
    quarkus.otel.metrics.exporter: "none"

    # Polaris event listener
    polaris.event-listener.types: "opentelemetry"
    polaris.event-listener.opentelemetry.enabled-event-types: "AFTER_UPDATE_TABLE"
```

Keep the existing `metrics.enabled: true`, `serviceMonitor.enabled: true`, and all authentication/storage config unchanged.

Note: if `helm template` from Task 1 Step 4 reveals that the 1.5.0 chart uses `advancedConfig:` instead of `configuration:`, or expects a different key format, adjust the key names here to match what the chart accepts. Do not switch to `extraEnv:` unless the chart provides no config-map path.

- [ ] **Step 2: Render and inspect**

```bash
helm template polaris /Users/kcl/Projects/retail-lakehouse/platform/21-polaris/ \
  --values /Users/kcl/Projects/retail-lakehouse/platform/21-polaris/values.yaml \
  | grep -A2 -E '(otel\.sdk|event-listener)'
```

Expected: both `quarkus.otel.sdk.disabled` and `polaris.event-listener.types` appear in the rendered ConfigMap or environment.

- [ ] **Step 3: Commit**

```bash
git add platform/21-polaris/values.yaml
git commit -m "feat(polaris): enable OTEL log export and AFTER_UPDATE_TABLE event listener"
```

---

## Task 3: Create OpenTelemetryCollector CR with a debug exporter

Rationale: we don't yet know the exact log-record attribute Polaris uses for the
table identifier. Ship the collector with a `debug` exporter first, generate a
real event in Task 6, read the attribute name off the debug log, then swap in the
Kafka exporter with the correct OTTL statement in Task 7.

**Files:**
- Create: `platform/22-polaris-events/otel-collector.yaml`

- [ ] **Step 1: Create the folder**

```bash
mkdir -p /Users/kcl/Projects/retail-lakehouse/platform/22-polaris-events
```

- [ ] **Step 2: Write the CR**

```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: polaris-events
  namespace: polaris
spec:
  mode: deployment
  replicas: 1
  image: otel/opentelemetry-collector-contrib:0.137.0
  config:
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
    processors:
      batch:
    exporters:
      debug:
        verbosity: detailed
    service:
      pipelines:
        logs:
          receivers: [otlp]
          processors: [batch]
          exporters: [debug]
```

The image tag matches the operator's default collector image tag from
`platform/11-otel-operator/values.yaml` (`0.137.0`).

- [ ] **Step 3: Commit (partial component; more files added in Task 4)**

```bash
git add platform/22-polaris-events/otel-collector.yaml
git commit -m "feat(polaris-events): scaffold OpenTelemetryCollector with debug exporter"
```

---

## Task 4: Create KafkaTopic CR

**Files:**
- Create: `platform/22-polaris-events/kafka-topic.yaml`

- [ ] **Step 1: Write the KafkaTopic**

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
    retention.ms: "604800000"
    cleanup.policy: delete
```

- [ ] **Step 2: Commit**

```bash
git add platform/22-polaris-events/kafka-topic.yaml
git commit -m "feat(polaris-events): declare polaris.table.commits KafkaTopic (1p/1r, 7d retention)"
```

---

## Task 5: Create bootstrap.sh, validate.sh, README.md

**Files:**
- Create: `platform/22-polaris-events/bootstrap.sh`
- Create: `platform/22-polaris-events/validate.sh`
- Create: `platform/22-polaris-events/README.md`

- [ ] **Step 1: Write bootstrap.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Polaris events pipeline deployed (OTEL collector + Kafka topic)"
log::on_failure "Polaris events pipeline deployment failed"

kubectl apply \
  -f "$SCRIPT_DIR/otel-collector.yaml" \
  --context "${KUBE_CONTEXT}"

kubectl apply \
  -f "$SCRIPT_DIR/kafka-topic.yaml" \
  --context "${KUBE_CONTEXT}"
```

- [ ] **Step 2: Write validate.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Polaris events pipeline is ready"
log::on_failure "Polaris events pipeline is not ready"

kubectl rollout status deployment/polaris-events-collector \
  --namespace polaris \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait \
  --for=condition=Ready kafkatopic/polaris.table.commits \
  --namespace kafka-cdc \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
```

- [ ] **Step 3: Make both scripts executable**

```bash
chmod +x /Users/kcl/Projects/retail-lakehouse/platform/22-polaris-events/bootstrap.sh \
         /Users/kcl/Projects/retail-lakehouse/platform/22-polaris-events/validate.sh
```

- [ ] **Step 4: Write README.md**

```markdown
# 22-polaris-events

Deploys the pipeline that turns Polaris table commit events into Kafka messages:

- `OpenTelemetryCollector` (`polaris-events` in namespace `polaris`) receives OTLP
  logs from Polaris on port 4317 and exports them to Kafka.
- `KafkaTopic` `polaris.table.commits` (namespace `kafka-cdc`, 1 partition,
  7 day retention) receives the events keyed by fully-qualified table id.

Depends on wave 20 (kafka-cluster, polaris-db) and wave 21 (polaris).

## Deploy

    KUBE_CONTEXT=retail-lakehouse ./bootstrap.sh
    KUBE_CONTEXT=retail-lakehouse ./validate.sh

## Consume events

    kubectl exec -n kafka-cdc kafka-cluster-dual-role-0 -- \
      bin/kafka-console-consumer.sh \
        --bootstrap-server localhost:9092 \
        --topic polaris.table.commits \
        --from-beginning \
        --property print.key=true
```

- [ ] **Step 5: Commit**

```bash
git add platform/22-polaris-events/bootstrap.sh \
        platform/22-polaris-events/validate.sh \
        platform/22-polaris-events/README.md
git commit -m "feat(polaris-events): add bootstrap/validate scripts and README"
```

---

## Task 6: Wire into tasks/apps.yml

**Files:**
- Modify: `tasks/apps.yml`

- [ ] **Step 1: Add validate line to `bootstrap-by-scripts.status:`**

In `tasks/apps.yml`, inside the `bootstrap-by-scripts:` task, append to the
`status:` list (right after the `22-kafka-iceberg-connector` line):

```yaml
      - TIMEOUT=10s bash platform/22-polaris-events/validate.sh
```

- [ ] **Step 2: Add bootstrap + validate lines to `bootstrap-by-scripts.cmds:`**

In the same task, inside `cmds:`, add these two lines immediately after the
`22-kafka-iceberg-connector` pair:

```yaml
      - bash platform/22-polaris-events/bootstrap.sh
      - bash platform/22-polaris-events/validate.sh
```

- [ ] **Step 3: Add parallel validate task**

Add a new dep to the top-level `validate:` task's `deps:` list:

```yaml
      - task: validate-polaris-events
        vars:
          KUBE_CONTEXT: "{{.KUBE_CONTEXT}}"
```

Then append this internal task at the end of the file:

```yaml
  validate-polaris-events:
    internal: true
    env:
      KUBE_CONTEXT: '{{.KUBE_CONTEXT}}'
    cmds:
      - bash platform/22-polaris-events/validate.sh
```

- [ ] **Step 4: Verify Task file parses**

Run:
```bash
task --list-all | grep polaris-events
```

Expected: shows `apps:validate-polaris-events` (or similar namespaced form).

- [ ] **Step 5: Commit**

```bash
git add tasks/apps.yml
git commit -m "chore(tasks): wire 22-polaris-events into apps bootstrap and validate"
```

---

## Task 7: Deploy and discover the Polaris table-id attribute

This task is discovery-driven. We roll out everything, generate a real commit
event, then read the debug exporter output to find the exact attribute name
Polaris uses. The result feeds into Task 8.

- [ ] **Step 1: Roll out the Polaris changes**

```bash
KUBE_CONTEXT=retail-lakehouse bash platform/21-polaris/bootstrap.sh
KUBE_CONTEXT=retail-lakehouse bash platform/21-polaris/validate.sh
```

Expected: `Polaris is ready` at the end. If the polaris-bootstrap job fails
because the 1.5.0 schema is incompatible with the 1.3.0-incubating DB, drop
and recreate the Polaris schema in postgres and retry (dev-only data):
```bash
kubectl exec -n polaris deploy/polaris-db -- \
  psql -U polaris -d polaris -c 'DROP SCHEMA IF EXISTS polaris_schema CASCADE;'
kubectl delete job polaris-bootstrap -n polaris --ignore-not-found \
  --context retail-lakehouse
KUBE_CONTEXT=retail-lakehouse bash platform/21-polaris/bootstrap.sh
```

- [ ] **Step 2: Roll out the events pipeline**

```bash
KUBE_CONTEXT=retail-lakehouse bash platform/22-polaris-events/bootstrap.sh
KUBE_CONTEXT=retail-lakehouse bash platform/22-polaris-events/validate.sh
```

Expected: `Polaris events pipeline is ready`.

- [ ] **Step 3: Tail the collector logs**

Open a terminal that keeps the log stream up:
```bash
kubectl logs -n polaris deploy/polaris-events-collector -f \
  --context retail-lakehouse
```

- [ ] **Step 4: Trigger a commit via Trino**

```bash
kubectl exec -n trino deploy/trino-coordinator -- \
  trino --catalog iceberg --execute "
    CREATE SCHEMA IF NOT EXISTS iceberg.tmp;
    CREATE TABLE IF NOT EXISTS iceberg.tmp.probe (id INT);
    INSERT INTO iceberg.tmp.probe VALUES (1);
  "
```

Expected: three statements execute successfully. The `INSERT` will produce an
`AFTER_UPDATE_TABLE` event in Polaris.

- [ ] **Step 5: Read the attribute name off the collector log**

In the collector log stream, locate the log record for the commit. It looks
roughly like:
```
LogRecord ...
Attributes:
  -> event.type: Str(AFTER_UPDATE_TABLE)
  -> <SOME.KEY>: Str(iceberg.tmp.probe)
  ...
```

Note the exact key that carries the value `iceberg.tmp.probe` (the fully-qualified
table id). Common candidates seen in Polaris source: `polaris.entity.identifier`,
`polaris.table.identifier`, `identifier`, `table_identifier`. Record the actual
key you observed — Task 8 uses it verbatim.

If no event appears within 30 seconds, verify Polaris's log shows event listener
init: `kubectl logs -n polaris deploy/polaris -c polaris | grep -i event-listener`.

---

## Task 8: Swap debug exporter for Kafka exporter with correct OTTL key

**Files:**
- Modify: `platform/22-polaris-events/otel-collector.yaml`

- [ ] **Step 1: Rewrite the collector config**

Replace the `spec.config` block in `otel-collector.yaml` with the final pipeline.
Substitute `<TABLE_ID_ATTR>` with the exact attribute name discovered in Task 7:

```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: polaris-events
  namespace: polaris
spec:
  mode: deployment
  replicas: 1
  image: otel/opentelemetry-collector-contrib:0.137.0
  config:
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
              - set(attributes["kafka.key"], attributes["<TABLE_ID_ATTR>"])
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
        logs:
          receivers: [otlp]
          processors: [transform/kafka-key, batch]
          exporters: [kafka/table-commits]
```

- [ ] **Step 2: Apply and roll**

```bash
kubectl apply \
  -f /Users/kcl/Projects/retail-lakehouse/platform/22-polaris-events/otel-collector.yaml \
  --context retail-lakehouse
kubectl rollout status deployment/polaris-events-collector -n polaris \
  --context retail-lakehouse
```

Expected: rollout completes. If the collector CrashLoops on start, `kubectl logs`
will name the mis-typed config key or unsupported field.

- [ ] **Step 3: Commit**

```bash
git add platform/22-polaris-events/otel-collector.yaml
git commit -m "feat(polaris-events): swap debug exporter for Kafka with table-id message key"
```

---

## Task 9: End-to-end smoke test

- [ ] **Step 1: Start a background consumer**

Open a terminal:
```bash
kubectl exec -n kafka-cdc kafka-cluster-dual-role-0 --context retail-lakehouse -- \
  bin/kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic polaris.table.commits \
    --from-beginning \
    --property print.key=true \
    --property key.separator=' | '
```

- [ ] **Step 2: Trigger three commits on distinct tables**

```bash
kubectl exec -n trino deploy/trino-coordinator --context retail-lakehouse -- \
  trino --catalog iceberg --execute "
    CREATE SCHEMA IF NOT EXISTS iceberg.tmp;
    CREATE TABLE IF NOT EXISTS iceberg.tmp.probe_a (id INT);
    CREATE TABLE IF NOT EXISTS iceberg.tmp.probe_b (id INT);
    INSERT INTO iceberg.tmp.probe_a VALUES (1);
    INSERT INTO iceberg.tmp.probe_b VALUES (10);
    INSERT INTO iceberg.tmp.probe_a VALUES (2);
  "
```

- [ ] **Step 3: Verify consumer output**

Expected: at least 3 records in the consumer output. Each record's key column
matches the table id used for the commit, e.g.:
```
iceberg.tmp.probe_a | { ... otlp_json ... AFTER_UPDATE_TABLE ... }
iceberg.tmp.probe_b | { ... }
iceberg.tmp.probe_a | { ... }
```

Two records for `probe_a` land on the same partition (there is only one
partition anyway, but the key-hash routing is what will preserve this once
partitions grow).

- [ ] **Step 4: Clean up the probe schema**

```bash
kubectl exec -n trino deploy/trino-coordinator --context retail-lakehouse -- \
  trino --catalog iceberg --execute "
    DROP TABLE iceberg.tmp.probe_a;
    DROP TABLE iceberg.tmp.probe_b;
    DROP SCHEMA iceberg.tmp;
  "
```

- [ ] **Step 5: Onboard-from-scratch verification**

To confirm the whole pipeline builds cleanly from an empty cluster:
```bash
task offboard KUBE_CONTEXT=retail-lakehouse
task onboard KUBE_CONTEXT=retail-lakehouse DEPLOY_METHOD=scripts
```

Expected: onboard succeeds end-to-end, including the new
`22-polaris-events/bootstrap.sh` and `22-polaris-events/validate.sh` lines,
and `Polaris events pipeline is ready` appears in the log.

---

## Self-Review Notes

Spec coverage:
- Polaris 1.3.0 → 1.5.0 upgrade (Task 1)
- OTEL SDK activation via Quarkus properties (Task 2)
- Event listener config, `AFTER_UPDATE_TABLE` only (Task 2)
- OpenTelemetryCollector CR in `polaris` namespace, name `polaris-events` (Tasks 3, 8)
- OTTL transform for message key (Task 8)
- Kafka exporter with `message_key_from_metadata_key` (Task 8)
- KafkaTopic `polaris.table.commits` 1p/1r/7d (Task 4)
- bootstrap.sh, validate.sh matching repo pattern (Task 5)
- tasks/apps.yml integration in both `bootstrap-by-scripts` and `validate` (Task 6)
- Attribute discovery step (Task 7) resolves the spec's flagged Open Question
- End-to-end smoke test through Trino (Task 9)

Non-coverage: `argocd` deploy method is intentionally not touched in this plan,
matching the current single-deployer focus of the task. If ArgoCD support is
required, it becomes a follow-up plan that adds an app-template under
`platform/02-argocd-apps/`.
