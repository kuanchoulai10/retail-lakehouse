# Platform (Infra)

- `platform/<NN>-<component>/` — each wave dir has `bootstrap.sh` + `validate.sh` (some `patch.sh`); the `NN` prefix is the deploy order.
- `tasks/apps.yml` `bootstrap-by-scripts` / `validate` chain the waves; this is the active deploy path. `bootstrap-by-argocd` exists but is on hold.
- `task onboard` / `task offboard` create / destroy the whole colima + minikube cluster and run all waves.
- Kubernetes namespaces cannot be renamed: a "rename" means deploy into the new namespace, then delete the old one. Data loss on minikube is acceptable.

## Cluster runtime

**Cluster runtime (2026-10-24):** single minikube node on colima, container runtime `containerd` (was `docker` / cri-dockerd, whose cAdvisor series had no `container` label, so prometheus-adapter served no pod metrics) with `--cni bridge` pinned (with containerd minikube would pick kindnet, which enforces the kube-prometheus and Strimzi NetworkPolicies and blocks KEDA → Prometheus and Kafka UI → Connect REST). `kubectl top nodes` / `kubectl top pods -A` work through prometheus-adapter. `cluster:configure-registry-mirror` writes `/etc/containerd/certs.d/<registry ClusterIP>/hosts.toml` (HTTP) because containerd ignores the CIDR given to `--insecure-registry`; Strimzi KafkaConnect images are pulled from that ClusterIP. istio-cni needs `cni.cniNetnsDir: /var/run/netns` on containerd (the `global.platform=minikube` preset assumes docker's `/var/run/docker/netns`, and ambient pods then hang in ContainerCreating with `failed to Statfs /host/var/run/netns/cni-…`).

## Deployed waves

**Deployed on minikube** (via `bootstrap-by-scripts`):
- Wave 10: cert-manager, kube-prometheus, Strimzi
- Wave 11: KEDA, Spark Operator, OTel Operator, Istio base, Gateway API CRDs
- Wave 12: istiod, istio-cni (`cni.cniNetnsDir: /var/run/netns`), ztunnel (PodMonitor `ztunnel` on :15020 `/metrics`, plus a Prometheus Role / RoleBinding in `istio-system` so kube-prometheus can discover it), `12-platform-gateway` (Gateway `platform-gateway` in `istio-ingress`, listener http :80 on any hostname, routes by path prefix, admits HTTPRoutes only from namespaces labelled `retail-lakehouse.io/gateway-routes=allowed`; routes table in its README; istiod registers the ext_authz extension provider `oauth2-proxy`)
- Wave 13: `13-identity` (namespace `identity`: Keycloak 26.8.2 + `keycloak-db` PostgreSQL 17.11, realm `retail-lakehouse` imported at first start, clients `oauth2-proxy` / `trino` / `platform-validate`, user `platform-admin` with a generated password in Secret `identity/keycloak-clients`; oauth2-proxy v7.15.6; HTTPRoutes `/keycloak` and `/sso`, both ungated; AuthorizationPolicy `platform-gateway-sso` (CUSTOM, provider `oauth2-proxy`) gates every other gateway path except `/polaris` behind a Keycloak session, plus `platform-gateway-sso-builtins` (DENY `/robots.txt`); validate scripts call the gate with a `platform-validate` bearer token via `gateway::curl`)
- Wave 20: Kafka (3 brokers), RustFS, MySQL, Polaris DB, Jaeger (trino / thanos), temporal-db (creates the `temporal` namespace; PostgreSQL for Temporal)
- Wave 21–22: Temporal server (chart `temporalio/temporal` 1.7.0, server 1.32.0; frontend `temporal-frontend.temporal.svc.cluster.local:7233`, Web UI `temporal-web:8080`, HTTPRoute `temporal-web` = `/temporal`, `TEMPORAL_UI_PUBLIC_PATH=/temporal`, Temporal namespace `default` with 3d retention), Polaris (also creates the `polaris-catalog-events` KafkaTopic in `kafka`; HTTPRoute `polaris` = `/polaris`, rewritten to `/`), 2 KafkaConnectors (debezium-mysql, iceberg-sink)
- Wave 23: Trino (CLI over mTLS; web UI logs in through Keycloak client `trino`, HTTPRoute `trino-ui` = `/ui` + `/oauth2` to `trino:8080` with `X-Forwarded-*` from the public origin; secrets `trino-internal-shared-secret` / `trino-credentials` generated or copied by `bootstrap.sh`, none in the repository), Kafka UI (HTTPRoute `kafka-ui` = `/kafka-ui`, `SERVER_SERVLET_CONTEXT_PATH=/kafka-ui`), Kiali (`23-kiali`, chart `kiali-server` 2.20.0 in `istio-system`, view-only with anonymous auth, 256Mi, Prometheus `prometheus-k8s.monitoring:9090`; web root `/kiali`, HTTPRoute `kiali` = `/kiali` on `platform-gateway`)
- Wave 25: lakehouse-control-plane (namespaces `lakehouse-control-plane`, `lakehouse-maintenance-operations`; Helm release `table-maintenance` = `table-maintenance-db` PostgreSQL, `migrate` Job, `api` (:8000), `worker`, `event-consumer`, `console` (nginx :8080, HTTPRoute `console` = `/console` on `platform-gateway`; open with `kubectl port-forward service/platform-gateway-istio 8591:80 --namespace istio-ingress --context retail-lakehouse` and browse `http://localhost:8591/console/`); images `table-maintenance-backend` / `table-maintenance-spark` / `console` built locally by `build.sh` and loaded into minikube; Spark jobs run in `lakehouse-maintenance-operations`, whose namespace is in the Spark operator `jobNamespaces`)

**Not deployed / on hold (do not touch unless the user re-opens them):**
- `platform/30-thanos`
- `platform/24-e2e-validation`
- ArgoCD path (`platform/00-argocd`, `01-argocd-health-checks`, `02-argocd-apps`, `charts/app-of-apps`)

## Ambient mesh

**Ambient mesh (L4, ztunnel only; no waypoints, no PeerAuthentication).** Enrolled namespaces (label `istio.io/dataplane-mode=ambient`): `kafka-ui`, `ecommerce-app`, `object-storage`, `lakehouse-catalog`, `kafka`, `lakehouse-query-engine`, `temporal`, `lakehouse-control-plane`, `lakehouse-maintenance-operations`, `identity`. Every wave that creates one of them creates it with the label (`namespace::apply_ambient` in `scripts/utils/namespace.sh`) and its `validate.sh` asserts it (`namespace::assert_ambient`); `mesh::assert_hbone <namespace>` checks every Running pod is HBONE in ztunnel. Callers outside the mesh (Prometheus, operators, KEDA, the gateway) stay plaintext under the permissive default.

Rule: a new application namespace is created with the ambient label. Exceptions:
- Never enrolled: `thanos` (on hold), `istio-system` (Istio's own namespace: a circular dependency), `istio-ingress` (the gateway is already a mesh proxy) and `kube-system` (host-network pods, excluded by istio-cni, and DNS is at risk).
- Not enrolled by default: operator namespaces (cert-manager, strimzi-operator, keda, spark-operator, opentelemetry-operator; their traffic goes to the apiserver, which is outside the mesh and already TLS) and `monitoring` (kept outside so that it can still diagnose a broken mesh).

## Kubernetes labels

Applies to every object we author (`platform/**/*.yaml` and the wave-25 chart); third-party charts, vendored charts, CRD bundles and patches of third-party objects keep their own labels. Enforced by `scripts/check_k8s_labels.py` (pre-commit hook `k8s-labels`, tests in `scripts/tests/`).

- **Recommended labels on every object:** `app.kubernetes.io/name` (the software: `postgres`, `kafka-ui`, `table-maintenance`), `app.kubernetes.io/instance` (which one: `polaris-db`, the Helm release), `app.kubernetes.io/part-of` (the system: `polaris`, `temporal`, `cdc`, `table-maintenance`), `app.kubernetes.io/managed-by` (`kubectl` or `Helm`), and `app.kubernetes.io/component` (role: `database`, `api`, `ui`, `ingress`) where it applies. No `app` label and no unprefixed key.
- **Pod templates carry the same `app.kubernetes.io/*` values as their workload, plus `app.kubernetes.io/version`** = the tag of one of the pod's containers (not an init container); the one exception to "no unprefixed key" is Strimzi `Kafka` / `KafkaConnect` pod templates, which carry the plain `version` label (Kiali's fallback) = the spec's Kafka version, because Strimzi 0.46 strips every `app.kubernetes.io/*` key from pod-template labels in code (`Util.mergeLabelsOrAnnotations`; `labelsExclusionPattern` does not affect it). Kiali reads it for telemetry and warns "version label is missing" without it. Bump it with the image tag. Third-party charts get it through their pod-label values (`podLabels` in `21-polaris/values.yaml`); operator-managed pods (Strimzi entity operator) keep their own labels.
- **Selectors** (Deployment `matchLabels`, Service `selector`) use only `app.kubernetes.io/name` + `app.kubernetes.io/instance`, plus `app.kubernetes.io/component` when one instance runs several workloads (the wave-25 chart). Never `part-of`, `managed-by` or `version`: selectors are immutable.
- **Every workload gets its own `instance`** unless the selectors include `component`: a Job sharing a Service's `name` + `instance` would be selected by it (`polaris-bootstrap`, `rustfs-create-bucket`).
- **Our own label keys use the prefix `retail-lakehouse.io/`** (`retail-lakehouse.io/gateway-routes`). Vendor keys (`istio.io/dataplane-mode`, `strimzi.io/cluster`) keep their own prefix.
- **Annotations** only where a tool requires one (`strimzi.io/*`, `networking.istio.io/*`, `helm.sh/hook*`, `checksum/config`) or for non-identifying notes; never select on an annotation.
- **Select third-party pods by their own labels** (`app=ztunnel` for ztunnel, `app.kubernetes.io/name=entity-operator` for Strimzi).
