# Node memory relief and ambient mesh (L4) — design

Date: 2026-10-31. Two phases, done in order: first bring the node's memory down, then enrol the platform
namespaces in the Istio ambient mesh so that service-to-service traffic is encrypted and the owner can see who
calls whom.

## Intent

The Istio ambient control plane (`12-istiod`, `12-istio-cni`, `12-ztunnel`, profile `ambient`) and the Gateway API
(`11-gateway-api-crds`, `platform-gateway` in `istio-ingress`) are already deployed, but no namespace is enrolled, so
no pod traffic goes through ztunnel. The owner wants two things from the mesh: traffic between services encrypted
automatically, and a basic view of who calls whom. They said the mesh must not make the single-node cluster
unstable, and that the memory pressure has to be solved first.

## Current state (measured 2026-10-31)

- Node `retail-lakehouse`: 22.5 GiB of about 28 GiB used (80%); requests 46%, limits 71%.
- Largest pods: Kafka brokers `kafka-cluster-dual-role-{0,1,2}` at 3.4 / 3.0 / 1.0 GiB with no `resources` or
  `jvmOptions` on the `dual-role` KafkaNodePool (`platform/20-kafka-cluster/kafka-cluster.yaml`); Trino coordinator
  2.5 GiB and worker 2.1 GiB (already bounded); RustFS 1.7 GiB; Jaeger collector (`lakehouse-query-engine`) 760 MiB;
  Polaris 600 MiB; Prometheus 570 MiB; two KafkaConnect pods about 500 and 420 MiB.

## Goals

1. Phase 1: node memory at or below about 65% at idle, with every pod changed in this phase bounded by a memory
   limit, and nothing OOM-killed afterwards.
2. Phase 2: every application namespace enrolled in ambient mode (`istio.io/dataplane-mode=ambient`), so traffic
   between two enrolled pods is mTLS (HBONE) through ztunnel without changing any service.
3. Phase 2: Kiali shows the service graph from ztunnel's L4 metrics (who connects to whom, connection and byte
   counts, mTLS shown), reachable through `platform-gateway`.
4. Both phases reproducible from `task onboard KUBE_CONTEXT=retail-lakehouse`: labels, limits and Kiali live in
   the wave manifests and scripts, never applied by hand.

## Non-goals

- No waypoint proxies, so no L7 view (HTTP paths, status codes, latency) and no L7 authorization policies.
- No `PeerAuthentication` STRICT: the mesh stays permissive, so callers outside the mesh (Prometheus scraping,
  kubelet probes, operators) keep working.
- No distributed tracing through the mesh, no new Grafana dashboards.
- No change to the on-hold waves (`30-thanos`, `24-e2e-validation`, ArgoCD path).
- No CNI change (bridge stays).
- No separate enrolment wave and no per-workload restarts to bring running pods into the mesh.

## Anti-goals

- The cluster or a data path breaking because of the mesh: CDC MySQL → Kafka → Iceberg → Trino, the table
  maintenance control plane (Temporal, Spark jobs) and the console must keep working.
- A memory fix that trades pressure for OOM kills or restart loops.
- A failure that cannot be traced to one namespace.

## Decided with the owner

- Order: memory first, then the mesh.
- L4 only (ztunnel), no waypoints; "who calls whom" at the most basic level is enough.
- Visualisation: the lightest option that does not risk the cluster (owner left the choice to Claude → Kiali).
- **65% is a target, not a gate.** After Kafka, RustFS, Jaeger and the two KafkaConnect clusters are bounded, the
  mesh goes ahead as long as nothing is OOM-killed or restart-looping. Expect roughly 66–70%. Do not cut further:
  no Prometheus retention change, no Trino change, no broker count change, no colima resize.
- **The enrolment label lives in each wave's own namespace manifest**, not in a separate wave. A namespace is
  created with `istio.io/dataplane-mode: ambient`, so its pods start inside the mesh and nothing has to be
  restarted.
- **Rollout:**
  1. A `kafka-ui` canary on the running cluster.
  2. If the canary passes, add the labels and memory limits to every wave.
  3. Run one clean `task offboard` + `task onboard KUBE_CONTEXT=retail-lakehouse`. Onboard deploys and validates
     the waves in order, so a failure points at one wave, and so at one namespace.
- **If the `kafka-ui` canary fails for a CNI reason, stop.** Ship the memory work alone, with its own clean
  onboard, and report back with the evidence. No CNI change.

## Design (Claude's calls — the owner can override)

### Memory

- Kafka (`dual-role` KafkaNodePool in `platform/20-kafka-cluster/kafka-cluster.yaml`): `jvmOptions` with a 1 GiB
  heap (`-Xms` / `-Xmx`) and a memory request and limit of about 2.5 GiB. Lower these later only from
  measurements.
- Bound the next largest unbounded pods, each from its measured usage plus headroom: RustFS, the Jaeger
  collector (also cap its in-memory trace count if it uses memory storage) and the two KafkaConnect clusters. The
  builder first checks that each one is not already bounded.
- Measure with `kubectl top` before the change and again after the clean onboard. "Nothing OOM-killed" means no
  OOMKilled status and no rise in restart count over a 30-minute soak after onboard. Record the numbers in the wave
  READMEs and in the CLAUDE.md "Node memory pressure" follow-up.

### Which namespaces

- Enrolled: `kafka-ui`, `ecommerce-app`, `object-storage`, `lakehouse-catalog`, `kafka`, `lakehouse-query-engine`,
  `temporal`, `lakehouse-control-plane`, `lakehouse-maintenance-operations`.
- Not enrolled: `kube-system`, `istio-system`, `istio-ingress` (the gateway is its own proxy), `monitoring`, and the
  operator namespaces (cert-manager, strimzi-operator, keda, spark-operator, otel-operator).

### Where the label goes

- Every place that creates an enrolled namespace sets the label. Several waves create the same namespace:
  - `lakehouse-catalog`: `20-polaris-db` and `21-polaris`
  - `lakehouse-query-engine`: `20-jaeger-trino` and `23-trino`
  - `temporal`: `20-temporal-db` and `21-temporal`
  - `lakehouse-control-plane` and `lakehouse-maintenance-operations`: wave 25's loop, and `11-spark-operator` for
    the latter

  All of them set the label, so whichever runs first and any later `apply` agree. The builder finds every creation
  site, including Helm `createNamespace` and `kubectl create namespace` in scripts.
- Timing: Istio is installed in waves 11–12, before any enrolled workload starts.
  `lakehouse-maintenance-operations` is created in wave 11, before ztunnel, but its Spark pods start only later
  from wave 25, so they are captured.
- Every wave that creates an enrolled namespace has a `validate.sh` that checks the label is present.

### Metrics and Kiali

- `12-ztunnel` adds a PodMonitor (or ServiceMonitor) so kube-prometheus scrapes ztunnel, which makes the
  `istio_tcp_*` series exist.
- New wave `23-kiali`. It has to come after `platform-gateway` (wave 22), because its HTTPRoute can only be
  validated against a live gateway.
  - Use the official `kiali-server` Helm chart, pinned to a version that supports ambient.
  - Kiali runs in `istio-system`, view-only, with anonymous auth and the chart's standard read-only cluster RBAC.
    Its memory limit is about 256 MiB, and it points at `prometheus-k8s.monitoring`.
  - Its HTTPRoute lives in `istio-system` and attaches to `platform-gateway` by path prefix, like the console.
    The gateway's `allowedRoutes` is widened to `istio-system`.
- Kiali pass condition: the graph for `kafka`, `ecommerce-app` and `lakehouse-catalog` shows edges between
  enrolled workloads, with mTLS shown, for at least Debezium → Kafka and Iceberg Connect → Polaris / RustFS.
  - Callers outside the mesh (Prometheus, operators, KEDA, the gateway) stay plaintext under the permissive
    default. They may show up as unknown or non-mTLS sources, which is accepted.
  - If Kiali cannot draw an ambient L4 graph, the fallback is a Grafana panel over `istio_tcp_*`; record the reason.

### Canary (on the running cluster, before any wave change)

- Steps:
  1. Label the `kafka-ui` namespace.
  2. Restart its one Deployment once, so it reconnects. This is the canary only; nothing else is restarted.
  3. Confirm that ztunnel lists the pod with protocol HBONE (`istioctl ztunnel-config workloads` or ztunnel's
     admin endpoint).
  4. Confirm that Kafka UI's own `validate.sh` passes and that the page loads.
- Kafka is not enrolled yet, so mTLS to it cannot be shown. The canary proves only that capture works on the
  bridge CNI.
- After the canary, the label stays. The later wave change makes it permanent.

### Verification after the clean onboard

- `task validate` passes. That covers every wave, including each label check.
- Every enrolled workload shows HBONE in ztunnel.
- Data paths:
  - CDC: insert a row in MySQL and see it in Trino. Allow the known 5–10 min Iceberg sink delay.
  - `platform/25-lakehouse-control-plane/e2e.sh` passes.
  - The console and Kiali load through `platform-gateway`.
- Kiali's pass condition holds.
- The memory soak holds.
- If one namespace's workloads fail because of the mesh, take its label out of its waves, record why, and
  re-onboard the rest. A failure shared by all namespaces stops the work.

### Docs

- In CLAUDE.md:
  - Replace "New namespaces are not labeled ambient…" with the enrolled list and this rule: a new application
    namespace is created with the ambient label. The exceptions and their reasons:
    - Never enrolled: Istio's own `istio-system` (a circular dependency), the gateway's `istio-ingress` (already
      a mesh proxy) and `kube-system` (host-network pods, excluded by istio-cni, and DNS is at risk).
    - Not enrolled by default: operator namespaces (their traffic goes to the apiserver, which is outside the mesh
      and already TLS) and `monitoring` (kept outside so that it can still diagnose a broken mesh).
  - Add `23-kiali` to the deployed list.
  - Update the memory follow-up.

## Left to the builder

- Exact heap and limit values, chosen from measurements.
- Kiali chart version and HTTPRoute path.
- How validate.sh checks HBONE (istioctl, ztunnel admin endpoint or Kiali API).
- Number of commits.
