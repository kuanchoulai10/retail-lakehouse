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
4. Both phases reproducible from `task onboard KUBE_CONTEXT=retail-lakehouse` (labels and Kiali in the wave
   scripts, not applied by hand).

## Non-goals

- No waypoint proxies, so no L7 view (HTTP paths, status codes, latency) and no L7 authorization policies.
- No `PeerAuthentication` STRICT: the mesh stays permissive, so callers outside the mesh (Prometheus scraping,
  kubelet probes, operators) keep working.
- No distributed tracing through the mesh, no new Grafana dashboards.
- No change to the on-hold waves (`30-thanos`, `24-e2e-validation`, ArgoCD path).
- No CNI change (bridge stays).

## Anti-goals

- The cluster or a data path breaking because of the mesh: CDC MySQL → Kafka → Iceberg → Trino, the table
  maintenance control plane (Temporal, Spark jobs) and the console must keep working after each enrolment.
- A memory fix that trades pressure for OOM kills or restart loops.
- Enrolling everything in one step, so that a failure cannot be traced to one namespace.

## Decided with the owner

- Order: memory first, then the mesh.
- L4 only (ztunnel), no waypoints; "who calls whom" at the most basic level is enough.
- Visualisation: the lightest option that does not risk the cluster (owner left the choice to Claude → Kiali, below).
- Namespaces are enrolled one at a time, each verified before the next, with rollback by removing the label.

## Design (Claude's calls — the owner can override)

### Phase 1: memory

- Kafka (`dual-role` KafkaNodePool): set `jvmOptions` (`-Xms` / `-Xmx`, about 1 GiB heap) and `resources` (memory
  request and limit around 2 GiB). Strimzi rolls the brokers one at a time; `min.insync.replicas: 2` keeps topics
  writable during the roll.
- Bound the next largest unbounded pods where it is safe: RustFS, Jaeger collector (also cap its in-memory trace
  count if it uses memory storage), the two KafkaConnect clusters. Each limit is set from its measured usage with
  headroom; the builder checks each one is not already bounded.
- Measure with `kubectl top` before and after; record the numbers in the wave READMEs and the CLAUDE.md
  "Node memory pressure" follow-up.

### Phase 2: mesh

- Enrolment is a namespace label set by wave `26-ambient-mesh` (see "Settled after the builder check"), and checked by
  that wave's `validate.sh`.
- Namespaces to enrol: `kafka-ui` first (canary: stateless, low impact), then `ecommerce-app`, `object-storage`,
  `lakehouse-catalog`, `kafka`, `lakehouse-query-engine`, `temporal`, `lakehouse-control-plane`,
  `lakehouse-maintenance-operations`. Not enrolled: `kube-system`, `istio-system`, `istio-ingress` (the gateway is
  its own proxy), `monitoring`, and operator namespaces (cert-manager, strimzi-operator, keda, spark-operator,
  otel-operator).
- Per enrolment: label, then restart nothing unless needed (ambient captures without restarts), then verify that
  namespace's validate.sh, that ztunnel lists its workloads with protocol HBONE, and the end-to-end data paths it
  takes part in. A failure means removing the label and recording why before going on.
- Canary risk to check first: istio-cni has never redirected traffic on this bridge-CNI node. If the canary fails
  for a CNI reason, stop and bring it back to the owner instead of working around it.
- Metrics: kube-prometheus scrapes ztunnel (PodMonitor or ServiceMonitor in the ztunnel wave) so
  `istio_tcp_*` series exist.
- Kiali: in wave `platform/26-ambient-mesh` (see "Settled after the builder check"), after Prometheus and
  istiod), official `kiali-server` Helm chart pinned, anonymous auth (dev cluster, no auth today anywhere), pointing
  at `prometheus-k8s.monitoring`, memory limit about 256 MiB. Exposed through an HTTPRoute on `platform-gateway`
  (path prefix, like the console).
- CLAUDE.md: replace "New namespaces are not labeled ambient…" with the enrolled list and the rule for new
  namespaces; add the waves to the deployed list.

## Settled after the builder check

Decided by the owner:

- **65% is a target, not a gate.** Phase 1 bounds Kafka, RustFS, Jaeger and the two KafkaConnect clusters, then
  Phase 2 starts, provided nothing is OOM-killed or restart-looping. Expect roughly 66–70%. Do not cut further
  (no Prometheus retention change, no Trino change, no broker count change, no colima resize).
- **If the `kafka-ui` canary fails for a CNI reason, stop.** Ship Phase 1 alone and report back with the
  evidence. No CNI change.

Claude's calls:

- **Kafka roll.**
  - CDC may lag or stall for a few minutes during the roll; data loss on minikube is acceptable.
  - Between brokers, check that there are no under-replicated partitions (Strimzi rolls one at a time).
  - After the roll, insert a row in MySQL and see it in Trino. Allow the known 5–10 min Iceberg sink delay.
- **Memory limits.**
  - Start the Kafka limit generously, about 2.5 GiB with a 1 GiB heap, and lower it later only from measurements.
  - "Nothing OOM-killed" means no OOMKilled or restart increase over a 30-minute soak after the last change.
- **Where enrolment lives.** A new last wave, `platform/26-ambient-mesh`, labels the namespaces listed in its
  bootstrap script, and its validate checks each one.
  - The rollout grows that list one namespace per commit, in the order above.
  - A fresh `task onboard` runs the same script after every other wave, so both use one code path, and no earlier
    wave enrols anything at namespace creation.
  - The wave also holds the ztunnel scrape config, Kiali and the Kiali HTTPRoute.
- **Verification per namespace.**
  - That namespace's `validate.sh` passes.
  - Its workloads show protocol HBONE in ztunnel (`istioctl ztunnel-config workloads`, or ztunnel's admin
    endpoint).
  - The data paths it is part of still work: CDC insert → Trino for `ecommerce-app`, `kafka`, `object-storage`,
    `lakehouse-catalog` and `lakehouse-query-engine`; `platform/25-lakehouse-control-plane/e2e.sh` for `temporal`,
    `lakehouse-control-plane` and `lakehouse-maintenance-operations`; the console through `platform-gateway`.
  - If a namespace fails for a reason specific to it, remove its label, record why, and continue with the rest.
    If it fails for a reason shared by all namespaces, stop.
- **Restarts.**
  - Existing connections stay plaintext until they reconnect, so after labelling, restart that namespace's
    workloads (`kubectl rollout restart`, one workload at a time).
  - Strimzi pods are deleted one at a time, waiting for the cluster to be ready in between.
  - "mTLS verified" means the connections made after that restart.
- **Callers outside the mesh** (Prometheus, operators, KEDA, the gateway) stay plaintext under the permissive
  default. They may appear in Kiali as unknown or non-mTLS sources; that is accepted.
- **Kiali.**
  - It runs in `istio-system`, with view-only mode, anonymous auth and the chart's standard read-only cluster
    RBAC.
  - Pick a chart version that supports ambient.
  - The HTTPRoute lives in `istio-system`, and the `platform-gateway` `allowedRoutes` is widened to `istio-system`.
  - Pass condition: the graph for `kafka`, `ecommerce-app` and `lakehouse-catalog` shows edges between enrolled
    workloads, with mTLS shown, for at least Debezium → Kafka and Iceberg Connect → Polaris / RustFS.
  - If Kiali cannot draw an ambient L4 graph, a Grafana panel over `istio_tcp_*` is the fallback; record the
    reason.

## Left to the builder

- Exact heap and limit values, chosen from measurements.
- Kiali chart version and wave number, HTTPRoute path.
- How validate.sh checks HBONE (istioctl, ztunnel admin endpoint or Kiali API).
- Number of commits (one per namespace enrolment is fine).
