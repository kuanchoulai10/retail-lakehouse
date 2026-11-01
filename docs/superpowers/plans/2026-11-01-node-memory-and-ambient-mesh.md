# Node Memory Relief and Ambient Mesh (L4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound the largest unbounded pods so the node drops from 80% memory, then enrol every application
namespace in the Istio ambient mesh (L4 mTLS through ztunnel) and show who calls whom in Kiali.

**Architecture:**
- Memory limits go into the existing wave manifests.
- Each wave that creates an application namespace creates it with `istio.io/dataplane-mode: ambient` through
  one shared shell helper, and checks the label in its `validate.sh`.
- The order is fixed:
  1. A `kafka-ui` canary on the running cluster proves capture works on the bridge CNI.
  2. ztunnel metrics and a new `23-kiali` wave are added.
  3. One clean `task offboard` + `task onboard` brings everything up enrolled from the start, with no
     restarts.

**Tech Stack:** Bash wave scripts, kubectl, Helm, Strimzi CRs, OpenTelemetry Collector CR (Jaeger), Istio
1.26.8 ambient (ztunnel), kube-prometheus PodMonitor, Kiali `kiali-server` Helm chart, Gateway API HTTPRoute,
Taskfile.

**Spec:** `docs/superpowers/specs/2026-10-31-node-memory-and-ambient-mesh-design.md`

## Global Constraints

- **Enrolment.**
  - Enrolled namespaces: `kafka-ui`, `ecommerce-app`, `object-storage`, `lakehouse-catalog`, `kafka`,
    `lakehouse-query-engine`, `temporal`, `lakehouse-control-plane`, `lakehouse-maintenance-operations`.
  - Never labelled: `kube-system`, `istio-system`, `istio-ingress`, `monitoring`, cert-manager, strimzi-operator,
    keda, spark-operator, otel-operator (and `thanos`, which is on hold).
  - Label key and value, exactly: `istio.io/dataplane-mode=ambient`.
  - The scope is L4 only: no waypoints, no `PeerAuthentication`, no CNI change (bridge stays).
  - No separate enrolment wave. Workloads are not restarted to enrol them, except the one canary restart in
    Task 2.
- **Memory.**
  - 65% node memory is a target, not a gate. Do not cut further: no Prometheus retention change, no Trino change,
    no broker count change, no colima resize.
  - Kafka gets a 1 GiB heap (`-Xms1g -Xmx1g`) and a memory request and limit of about 2.5 GiB.
  - Every other limit comes from measured usage plus headroom.
  - The soak is 30 minutes after the last change, with no OOMKilled status and no rise in restart count.
- **CNI stop rule.** If the `kafka-ui` canary fails for a CNI reason, STOP the mesh work:
  - Revert the canary label.
  - Finish Task 1 with its own clean onboard.
  - Report back with the evidence.
- **Kiali.**
  - Runs in `istio-system`: view-only, anonymous auth, the chart's read-only cluster RBAC, a memory limit of about
    256 MiB, and Prometheus at `http://prometheus-k8s.monitoring:9090`.
  - Reached through an HTTPRoute on `platform-gateway`. The gateway's `allowedRoutes` is widened to
    `istio-system`.
- **Shell and repo rules.**
  - No `cd`. Use absolute paths or `--directory` / `--context`.
  - `kubectl <verb>` comes first, then flags. `kubectl scale/patch/replace/annotate` and `rm -rf` are blocked by a
    hook: never work around them. `kubectl label` and `kubectl rollout restart` are allowed.
  - Pass `KUBE_CONTEXT=retail-lakehouse` explicitly, and use `uv run` for any Python.
  - No explanatory comments in YAML.
  - Commits are conventional, on `main`, with lines of at most 100 chars, ending with a blank line and
    `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`. Never push, never stage
    `docs/architecture.excalidraw.svg`, and stage files by explicit path.
  - Every commit passes `task pre-pr`. shellcheck runs on scripts through pre-commit.

## Review Focus

1. **Re-running a wave against an existing, unlabelled namespace.** The helper must add the label: the
   generated manifest carries it, and `kubectl apply` merges it. Pinned by Task 2, Step 4, which checks the
   label is idempotent on re-apply.
2. **Callers outside the mesh reaching enrolled pods.** This covers Prometheus scraping, kubelet probes,
   `platform-gateway` → console / Polaris / Kiali, and the operators (Strimzi, Spark operator). They must keep
   working under the permissive default. Pinned by Task 5, Step 4: Prometheus target health and the gateway
   routes.
3. **Spark driver and executor pods in `lakehouse-maintenance-operations`** reach the API's result callback and
   each other through ztunnel. Pinned by Task 5, Step 5 (`e2e.sh`).
4. **A Kafka broker at its new limit during a CDC burst or the roll.** It must not be OOM-killed. Pinned by
   Task 1, Step 5 (under-replicated check plus a CDC insert) and the Task 5 soak.
5. **The Kiali graph shows nothing because ztunnel series are missing or mislabelled.** Pinned by Task 4,
   Step 2 (an `istio_tcp_sent_bytes_total` series from ztunnel exists in Prometheus) and Task 5, Step 6 (graph
   pass condition).

---

### Task 1: Bound Kafka, KafkaConnect, RustFS and Jaeger memory

**Files:**
- Modify: `platform/20-kafka-cluster/kafka-cluster.yaml` (the `dual-role` KafkaNodePool `spec`)
- Modify: `platform/21-kafka-debezium-mysql-connector/debezium-connect-cluster.yaml`
- Modify: `platform/22-kafka-iceberg-connector/iceberg-connect-cluster.yaml`
- Modify: `platform/20-rustfs/rustfs.yaml` (the `rustfs` container)
- Modify: `platform/20-jaeger-trino/jaeger.yaml` (`spec.resources`, and `max_traces` under `jaeger_storage`)
- Modify: the `README.md` of each of those waves, plus the CLAUDE.md "Node memory pressure" follow-up

**Interfaces:** none consumed. Produces bounded pods for Task 5's soak.

- [ ] **Step 1: Measure before.** Run `kubectl top nodes --context retail-lakehouse` and
  `kubectl top pods --all-namespaces --sort-by=memory --context retail-lakehouse`. Save the output to the job's
  tmp dir. Expected: node at about 80%; brokers about 3.4 / 3.0 / 1.0 GiB.
- [ ] **Step 2: Kafka.**
  - On the KafkaNodePool, set `jvmOptions: {-Xms: 1g, -Xmx: 1g}` and
    `resources: {requests: {memory: 2560Mi}, limits: {memory: 2560Mi}}`.
  - Change no other Kafka setting.
- [ ] **Step 3: Connect, RustFS and Jaeger.** Before each one, confirm with `kubectl get … -o yaml` that it is
  not already bounded.
  - Each KafkaConnect: `jvmOptions` heap about 512m and a memory limit about 1Gi (request = limit).
  - RustFS: a memory request and limit from measured usage plus about 30% headroom.
  - Jaeger: lower `max_traces` from 100000 to 20000, and set a memory request and limit of about 512Mi.
  - If a measured number argues for another value, use it and record why in that wave's README.
- [ ] **Step 4: Apply on the running cluster.** Run, in this order:
  1. `bash platform/20-kafka-cluster/bootstrap.sh`
  2. the 21 / 22 connector bootstraps
  3. `20-rustfs`
  4. `20-jaeger-trino`

  Use `KUBE_CONTEXT=retail-lakehouse` on each. While Strimzi rolls the brokers one at a time, check that no
  partition is under-replicated between brokers: `kafka-topics.sh --describe --under-replicated-partitions`
  inside a broker pod, which must print nothing once each broker is ready.
- [ ] **Step 5: Verify.**
  - Each touched wave's `validate.sh` passes.
  - Insert one row into a MySQL table that the CDC pipeline mirrors, and see it in Trino. Allow 5–10 minutes,
    because of the known Iceberg sink delay.
  - No pod in `kafka`, `object-storage` or `lakehouse-query-engine` shows `OOMKilled` or a rising restart count
    after 30 minutes.
- [ ] **Step 6: Measure after.** Record the before / after numbers in each wave's README and in the CLAUDE.md
  memory follow-up.
- [ ] **Step 7: Commit.** `fix(platform): bound Kafka, Connect, RustFS and Jaeger memory`.

### Task 2: Ambient namespace helper and `kafka-ui` canary

**Files:**
- Create: `scripts/utils/namespace.sh`
- Modify: `platform/23-kafka-ui/bootstrap.sh`, `platform/23-kafka-ui/validate.sh`

**Interfaces:**
- Produces, in `scripts/utils/namespace.sh`. The file is sourced like `log.sh`, with a load guard, and every
  function reads `KUBE_CONTEXT`.
  - `namespace::apply_ambient <name>`: create-or-update the namespace with label
    `istio.io/dataplane-mode=ambient`. Implement it as
    `kubectl create namespace … --dry-run=client -o yaml`, then `kubectl label --local -f - … -o yaml`, then
    `kubectl apply -f -`.
  - `namespace::assert_ambient <name>`: exit non-zero with a clear message unless the label is present with
    value `ambient`.
  - `mesh::assert_hbone <namespace>`: exit non-zero unless every Running pod in the namespace appears in
    ztunnel's workload config with protocol `HBONE`. Read ztunnel's admin `config_dump` (port 15000) through
    `kubectl port-forward` to a ztunnel pod in `istio-system`, because istioctl is not installed. Stop the
    port-forward on exit.
- Consumes `log.sh`.

- [ ] **Step 1: Write the failing check.** Add `namespace::assert_ambient kafka-ui` and
  `mesh::assert_hbone kafka-ui` to `23-kafka-ui/validate.sh`, with the helper stubbed to return 1.
- [ ] **Step 2: Run it.** `KUBE_CONTEXT=retail-lakehouse bash platform/23-kafka-ui/validate.sh`. Expected: FAIL,
  with the label-missing message.
- [ ] **Step 3: Implement.** Write the three helper functions, and replace the inline namespace creation in
  `23-kafka-ui/bootstrap.sh` with `namespace::apply_ambient kafka-ui`.
- [ ] **Step 4: Canary on the running cluster.**
  1. Run `bash platform/23-kafka-ui/bootstrap.sh` twice. The second run must not fail, and the label must still be
     set.
  2. Run `kubectl rollout restart deployment/kafka-ui --namespace kafka-ui --context retail-lakehouse`. This is
     the only restart in the plan.
  3. Run the validate again. Expected: PASS ("Kafbat UI is ready"), with the kafka-ui pod listed as HBONE.
  4. Confirm that the Kafka UI page loads and lists the cluster's topics through a port-forward to its Service.
- [ ] **Step 5: CNI stop rule.** If Step 4 fails because the pod is not captured (no HBONE, or istio-cni or ztunnel
  errors about redirection):
  1. Remove the label with `kubectl label namespace kafka-ui istio.io/dataplane-mode-`.
  2. Revert this task's files.
  3. Record the ztunnel and istio-cni logs in the job tmp dir.
  4. STOP the plan after a clean onboard of Task 1 only, and report.
- [ ] **Step 6: Commit.** `feat(platform): enrol kafka-ui in the ambient mesh`.

### Task 3: Label every other application namespace in its waves

**Files:**
- Modify the `bootstrap.sh` (namespace creation) and `validate.sh` (add `namespace::assert_ambient <ns>`) of:
  `11-spark-operator` (`lakehouse-maintenance-operations` only, not the operator's own namespace),
  `20-kafka-cluster`, `20-rustfs`, `20-mysql`, `20-polaris-db`, `20-jaeger-trino`, `20-temporal-db`, `21-polaris`,
  `21-temporal`, `23-trino`, and `25-lakehouse-control-plane` (the loop over both namespaces).
- Modify `platform/21-polaris/README.md`, which shows a manual `kubectl create namespace lakehouse-catalog`.

**Interfaces:** consumes `namespace::apply_ambient` and `namespace::assert_ambient` from Task 2.

- [ ] **Step 1: Enumerate.** Run
  `grep -rn -e 'create namespace' -e 'create-namespace' -e 'createNamespace' platform`, excluding the on-hold
  waves. Every hit for an enrolled namespace must be in the file list above. Add any hit that is missing.
- [ ] **Step 2: Write the failing checks.** Add `namespace::assert_ambient` for each enrolled namespace to its
  waves' `validate.sh`. Run one, for example `KUBE_CONTEXT=retail-lakehouse bash platform/20-mysql/validate.sh`.
  Expected: FAIL, label missing.
- [ ] **Step 3: Implement.** Replace each inline creation with `namespace::apply_ambient <ns>`. Wave 25 calls it
  inside its existing loop.
- [ ] **Step 4: Do not apply to the running cluster.** Pods would be captured live while holding old plaintext
  connections. Task 5's clean onboard applies these changes. Check the scripts statically: run
  `bash -n` on each script and let shellcheck run through pre-commit.
- [ ] **Step 5: Commit.** `feat(platform): create application namespaces in the ambient mesh`. Expect
  `task validate` to fail on these label checks against the current cluster until Task 5.

### Task 4: ztunnel metrics and the `23-kiali` wave

**Files:**
- Create: `platform/12-ztunnel/ztunnel-podmonitor.yaml` (`monitoring.coreos.com/v1` PodMonitor selecting the
  ztunnel pods, metrics port 15020, path `/stats/prometheus`). Apply it from `12-ztunnel/bootstrap.sh`, and check
  it exists in `validate.sh`.
- Create: `platform/23-kiali/{bootstrap.sh,validate.sh,values.yaml,kiali-route.yaml,README.md}`.
- Modify: `platform/22-polaris-routes/gateway.yaml` (add `istio-system` to the `allowedRoutes` values).
- Modify: `tasks/apps.yml`. Add Kiali bootstrap + validate after `23-trino` in `bootstrap-by-scripts`, the
  validate in the `validate` status list, and a `validate-kiali` internal task, mirroring
  `validate-kafka-ui`.

**Interfaces:**
- Kiali Service `kiali` in `istio-system`, port 20001.
- HTTPRoute `kiali` in `istio-system`, `PathPrefix /kiali`, parentRef `platform-gateway` in `istio-ingress`.
- Kiali `server.web_root: /kiali`.

- [ ] **Step 1: Write the failing check.** Write `23-kiali/validate.sh`. It checks:
  - the `kiali` Deployment rollout,
  - the HTTPRoute `kiali` reports `Accepted=True` (conditions are at `.status.parents[]`),
  - `GET /kiali/api/status` through a gateway port-forward returns 200.

  Run it. Expected: FAIL, because the Deployment is not found.
- [ ] **Step 2: ztunnel metrics.**
  - Apply the PodMonitor with `bash platform/12-ztunnel/bootstrap.sh`.
  - Within 2 minutes, a Prometheus query for `istio_tcp_sent_bytes_total` returns at least one series whose
    source or destination is the kafka-ui workload. Query through a port-forward to `prometheus-k8s` in
    `monitoring`.
  - If no series appears, compare the port and path with the live ztunnel pod spec before changing anything
    else.
- [ ] **Step 3: Kiali.**
  - `bootstrap.sh` installs Helm repo `https://kiali.org/helm-charts`, chart `kiali-server`, pinned to the newest
    version whose compatibility list includes Istio 1.26. Record the version and the reason in the README.
  - Install into `istio-system` with `values.yaml`, which sets:
    - `auth.strategy: anonymous`
    - `deployment.view_only_mode: true`
    - `deployment.resources` memory request about 128Mi and limit 256Mi
    - `external_services.prometheus.url: http://prometheus-k8s.monitoring:9090`
    - `server.web_root: /kiali`
    - Grafana and tracing integrations disabled
  - Then apply `kiali-route.yaml`, and re-apply `22-polaris-routes/gateway.yaml`.
- [ ] **Step 4: Run validate.** Expected: PASS. Also open `/kiali` in a browser through the gateway port-forward
  and check that the graph page loads. Only the kafka-ui edges may show at this point.
- [ ] **Step 5: Commit.** `feat(platform): scrape ztunnel and add Kiali behind platform-gateway`.

### Task 5: Clean onboard, full verification and docs

**Files:**
- Modify: `CLAUDE.md`:
  - Replace "New namespaces are **not** labeled…" with the enrolled list and the rule. Use the spec's "Docs"
    section, with the reasons for the exceptions.
  - Add `23-kiali` to the wave 23 deployed line.
  - Add the PodMonitor to the wave 12 line.
  - Update the memory follow-up.
  - Add a 2026-11-01 history line.
- Modify: `platform/12-ztunnel/README.md` (enrolment, the HBONE check and the PodMonitor).

**Interfaces:** consumes everything above.

- [ ] **Step 1: Offboard.** Run `task offboard`. The owner approved this clean rebuild in the spec. Then confirm
  that the lima disk was deleted, per the memory note `offboard-must-delete-lima-disk`.
- [ ] **Step 2: Onboard.** Run `task onboard KUBE_CONTEXT=retail-lakehouse`. Expected: every wave's bootstrap and
  validate passes, including the label checks and `23-kiali`. If a wave fails because of the mesh:
  - If the failure is in one namespace, take that namespace's label out of its waves, record why in its README,
    and re-onboard.
  - If every namespace fails the same way, STOP and report.
- [ ] **Step 3: HBONE.** Run `mesh::assert_hbone` for each of the nine enrolled namespaces. Expected: all pass.
- [ ] **Step 4: Outside callers.**
  - Prometheus: every target in the `/api/v1/targets` output that points at an enrolled namespace has
    `health: up`.
  - `platform-gateway` routes: `/console/` returns 200, Polaris through its route returns 200, and `/kiali`
    returns 200.
- [ ] **Step 5: Data paths.**
  - CDC: insert a row in MySQL and see it in Trino. Allow 5–10 minutes.
  - `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e.sh` passes.
- [ ] **Step 6: Kiali graph.** For `kafka`, `ecommerce-app` and `lakehouse-catalog`, the graph shows these
  enrolled-to-enrolled edges with mTLS shown:
  - Debezium Connect → Kafka
  - Iceberg Connect → Polaris
  - Iceberg Connect → RustFS

  Check it through the Kiali API (`/kiali/api/namespaces/graph?namespaces=…`, with each edge's
  `isMTLS`/`security` field) and with one screenshot. If Kiali cannot draw ambient L4 edges, record the reason
  and add a Grafana panel over `istio_tcp_*` as the spec's fallback.
- [ ] **Step 7: Memory soak.** Wait 30 minutes after onboard, then take `kubectl top` again. Expected:
  - no `OOMKilled` status and no rising restart counts in any namespace,
  - the node near 65% (a target, not a gate).

  Record the numbers.
- [ ] **Step 8: Commit the docs.** `docs(platform): record ambient enrolment, Kiali and memory limits`.
