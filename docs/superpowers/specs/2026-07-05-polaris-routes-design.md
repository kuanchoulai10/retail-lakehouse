# Polaris Routes — Design

**Date**: 2026-07-05
**Status**: Draft
**Related**: [Istio Ambient Onboard Design (2026-07-04)](2026-07-04-istio-ambient-onboard-design.md)

## Motivation

The Istio ambient onboard (2026-07-04) installed the control plane, dataplane, and an Envoy-based ingress gateway, but no `Gateway`/`HTTPRoute` resources yet exist. This design adds the first routing layer: a single Gateway that exposes Polaris as the default backend and the table-maintenance backend under the `/v1/` path prefix. As part of consolidating routing, all `table-maintenance-*` workloads (backend, scheduler, db, spark job) are relocated from the `default` namespace to the `polaris` namespace so that HTTPRoutes can reference them in-namespace without `ReferenceGrant` boilerplate.

## Scope

**In scope**
- New `platform/22-polaris-routes/` directory containing:
  - `Gateway` "platform-gateway" in `istio-ingress` namespace.
  - `HTTPRoute` "polaris-catchall" in `polaris` namespace (default backend).
  - `HTTPRoute` "backend-route" in `polaris` namespace (path prefix `/v1/`).
  - `bootstrap.sh`, `validate.sh`, `README.md`.
- Move all `table-maintenance-*` workloads to `polaris` namespace:
  - `platform/25-tbl-maint-bcknd/` (Deployment + Service + RBAC + validate).
  - `platform/25-tbl-maint-schdlr/` (Deployment + validate).
  - `platform/25-tbl-maint-db/` (Deployment + Service + PVC + validate).
  - `platform/25-table-maintenance/` (SparkApplication template).
- Wire `platform/22-polaris-routes/` into `tasks/apps.yml` `bootstrap-by-scripts`.
- Add `charts/app-of-apps/templates/22-polaris-routes.yaml`.

**Out of scope**
- External exposure of `istio-ingressgateway`. It stays `ClusterIP`; users test via `kubectl port-forward`.
- mTLS / TLS on the Gateway. HTTP only in this iteration.
- Ambient namespace enrollment (`istio.io/dataplane-mode=ambient` label) for `polaris` ns.
- Wiring wave 24 (`24-e2e-validation`) or wave 25 into `bootstrap-by-scripts` — those remain manual today, this design does not change that.
- Migrating existing PVC data from `default` to `polaris` namespace. Dev cluster only; `task offboard` destroys everything anyway.
- Adding routes for `trino`, `kafka-ui`, or any other cluster-internal service.

## Key Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Wave placement | 22 (after Polaris, before backend) |
| 2 | Routing rule shape | Single prefix `/v1/` → backend; everything else → Polaris |
| 3 | Gateway namespace | `istio-ingress` |
| 4 | HTTPRoute namespace | `polaris` (co-located with both backends) |
| 5 | Backend namespace | Moved from `default` to `polaris` in this change |
| 6 | Gateway `allowedRoutes` | `from: Selector`, matching `kubernetes.io/metadata.name = polaris` |
| 7 | GatewayClass | `istio` (default GatewayClass created by istio-cni + istiod install) |
| 8 | Gateway listener | Port 80, protocol HTTP (no TLS) |
| 9 | ReferenceGrant | Not needed (HTTPRoutes and their backends are in the same namespace) |
| 10 | External exposure of ingress gateway | None. Users test via `kubectl port-forward svc/istio-ingressgateway -n istio-ingress 8080:80` |
| 11 | HTTPRoute split strategy | Two HTTPRoutes (one per bounded context), not a single HTTPRoute with two rules |
| 12 | Backend match ordering | Rely on Gateway API's "most-specific match wins" — `/v1/` beats catchall |

## Architecture

```
User (laptop)
   │
   │  kubectl port-forward svc/istio-ingressgateway -n istio-ingress 8080:80
   ▼
┌─────────────────── istio-ingress ns ──────────────────┐
│  istio-ingressgateway (Envoy Deployment, ClusterIP)    │
│  Gateway "platform-gateway"                            │
│   └─ listener: port 80, protocol HTTP                  │
│      allowedRoutes.namespaces:                         │
│        from: Selector                                  │
│        selector: kubernetes.io/metadata.name = polaris │
└────────────────────────────────────────────────────────┘
   │
   │  Gateway API attaches HTTPRoutes from polaris ns
   ▼
┌────────────────────── polaris ns ─────────────────────┐
│                                                        │
│  HTTPRoute "backend-route"                             │
│   parentRefs: istio-ingress/platform-gateway           │
│   matches:    PathPrefix `/v1/`                        │
│   backendRefs: table-maintenance-backend:8000          │
│                                                        │
│  HTTPRoute "polaris-catchall"                          │
│   parentRefs: istio-ingress/platform-gateway           │
│   matches:    (none = catch-all)                       │
│   backendRefs: polaris:8181                            │
│                                                        │
│  Service: polaris (existing, wave 21)                  │
│  Service: table-maintenance-backend (moved from        │
│           default in this change; deploys wave 25)     │
│  Service: tbl-maint-db (moved from default)            │
└────────────────────────────────────────────────────────┘
```

## Wave Layout

| Wave | Action | Files |
|------|--------|-------|
| **22** (new) | Create `platform/22-polaris-routes/` with Gateway + two HTTPRoutes | 6 new files (bootstrap.sh, validate.sh, README.md, gateway.yaml, polaris-httproute.yaml, backend-httproute.yaml) |
| **25** (modify) | Update `namespace: default` → `polaris` across 4 wave-25 directories | 10 yaml + 3 validate.sh + 1 SparkApplication yaml |
| `tasks/apps.yml` | Add wave-22 to `bootstrap-by-scripts` status + cmds | 3 lines |
| `charts/app-of-apps/templates/` | New `22-polaris-routes.yaml` ArgoCD Application | 1 new file |

### Timing behaviour

- Wave 22 executes after Polaris (wave 21) — `polaris/polaris` Service exists → `polaris-catchall` HTTPRoute attaches with `ResolvedRefs=True` immediately.
- Wave 22 executes before wave 25 — `polaris/table-maintenance-backend` Service does NOT yet exist → `backend-route` HTTPRoute stays `Accepted=True` but `ResolvedRefs=False` (`BackendNotFound`). This is the Gateway API standard lazy-resolution behaviour, not an error.
- When wave 25 is later run manually, the backend Service appears and the route auto-recovers to `ResolvedRefs=True`.
- The wave 22 `validate.sh` therefore checks only `Accepted=True`, not `ResolvedRefs`, so it passes even before wave 25 runs.

## Gateway Resource

**`platform/22-polaris-routes/gateway.yaml`**
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: platform-gateway
  namespace: istio-ingress
spec:
  gatewayClassName: istio
  listeners:
    - name: http
      port: 80
      protocol: HTTP
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              kubernetes.io/metadata.name: polaris
```

`gatewayClassName: istio` binds this Gateway to the `istio` GatewayClass installed by `istio/istiod`. Istio then wires the Gateway to the Envoy pods managed by the `istio/gateway` release in the `istio-ingress` namespace.

`allowedRoutes.namespaces.from: Selector` restricts HTTPRoute attachment to the `polaris` namespace only (matched by the built-in namespace label `kubernetes.io/metadata.name`). Any HTTPRoute in other namespaces referring to this Gateway will be rejected.

## HTTPRoutes

**`platform/22-polaris-routes/backend-httproute.yaml`**
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: backend-route
  namespace: polaris
spec:
  parentRefs:
    - name: platform-gateway
      namespace: istio-ingress
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /v1/
      backendRefs:
        - name: table-maintenance-backend
          port: 8000
```

**`platform/22-polaris-routes/polaris-httproute.yaml`**
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: polaris-catchall
  namespace: polaris
spec:
  parentRefs:
    - name: platform-gateway
      namespace: istio-ingress
  rules:
    - backendRefs:
        - name: polaris
          port: 8181
```

Two HTTPRoutes rather than one route with two rules: each bounded context owns its own route file, so future changes to backend or Polaris routing don't touch a shared resource. This matches the DDD ownership boundary already used in the codebase.

Gateway API "most-specific match wins" arbitrates between the two routes: a request to `/v1/foo` matches `backend-route`'s `/v1/` prefix (more specific than `polaris-catchall`'s empty match) and is sent to the backend. Requests like `/api/catalog/v1/namespaces` (Polaris's Iceberg REST) or `/foobar` fall through to `polaris-catchall`.

## Bootstrap and Validate Scripts

**`platform/22-polaris-routes/bootstrap.sh`**
```bash
#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "polaris-routes installed"
log::on_failure "polaris-routes installation failed"

kubectl apply --server-side \
  -f "$SCRIPT_DIR/gateway.yaml" \
  -f "$SCRIPT_DIR/polaris-httproute.yaml" \
  -f "$SCRIPT_DIR/backend-httproute.yaml" \
  --context "${KUBE_CONTEXT}"
```

**`platform/22-polaris-routes/validate.sh`**
```bash
#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "polaris-routes are Programmed"
log::on_failure "polaris-routes are not Programmed"

kubectl wait --for=condition=Programmed gateway/platform-gateway \
  --namespace istio-ingress \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait --for=condition=Accepted httproute/polaris-catchall \
  --namespace polaris \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait --for=condition=Accepted httproute/backend-route \
  --namespace polaris \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
```

Validation deliberately checks only `Accepted=True`, not `ResolvedRefs=True`. `Accepted` means the Gateway has admitted the HTTPRoute as valid; `ResolvedRefs` requires the referenced backend Service to exist. Because `backend-route` targets a Service that only appears in wave 25 (manual step), `ResolvedRefs` will legitimately be `False` at wave 22 execution time and must not fail the bootstrap.

## Wave 25 Namespace Migration

All four wave-25 directories move from `default` to `polaris` namespace. Concrete changes per file:

### `platform/25-tbl-maint-bcknd/`

- `backend-deployment.yaml`
  - `metadata.namespace`: `default` → `polaris`
  - Env `GLAC_POSTGRES__DB_URL`: `tbl-maint-db.default.svc` → `tbl-maint-db.polaris.svc`
- `backend-service.yaml`: `metadata.namespace: default` → `polaris`
- `backend-rbac.yaml`: 5 occurrences of `namespace: default` (ServiceAccount, Role, RoleBinding metadata + RoleBinding.subjects[0].namespace) → `polaris`
- `validate.sh`: 3 occurrences of `--namespace default` → `--namespace polaris`

### `platform/25-tbl-maint-schdlr/`

- `scheduler-deployment.yaml`
  - `metadata.namespace`: `default` → `polaris`
  - Env `GLAC_POSTGRES__DB_URL`: `tbl-maint-db.default.svc` → `tbl-maint-db.polaris.svc`
- `validate.sh`: 3 occurrences of `--namespace default` → `--namespace polaris`

### `platform/25-tbl-maint-db/`

- `postgres-service.yaml`: `metadata.namespace: default` → `polaris`
- `postgres-deployment.yaml`: `metadata.namespace: default` → `polaris`
- `postgres-pvc.yaml`: `metadata.namespace: default` → `polaris`
- `validate.sh`: 3 occurrences of `--namespace default` → `--namespace polaris`

### `platform/25-table-maintenance/`

- `sparkapplication-rewrite-data-files.yaml`: `metadata.namespace: default` → `polaris`

### Impact analysis

- **RBAC**: The Role granting SparkApplication CRUD is namespace-scoped. Moving it (with the SA and RoleBinding) to `polaris` ns keeps semantics identical, but restricts backend to trigger SparkApplications only in `polaris` ns. That matches the SparkApplication template which also moves to `polaris` ns.
- **Spark operator**: Cluster-scoped; watches SparkApplication in all namespaces. Moving the template doesn't affect operator behaviour.
- **PVC**: The tbl-maint-db PVC in `polaris` ns is a fresh volume — any existing data in the old `default`-ns PVC is left behind and would be garbage-collected on next `task offboard`. Acceptable for a dev cluster.
- **`polaris` namespace**: Already exists (created at wave 21 by the Polaris chart). No `CreateNamespace` required.

## `tasks/apps.yml` Integration

In the `bootstrap-by-scripts` `status:` block, append after the last existing wave-12 or wave-22 entry (e.g., after `platform/12-istio-ingressgw/validate.sh` from the previous design):
```yaml
- TIMEOUT=10s bash platform/22-polaris-routes/validate.sh
```

In the `cmds:` block, insert between the last wave-22 Kafka connector entry (`platform/22-kafka-iceberg-connector/validate.sh`) and the first wave-23 entry (`platform/23-kafka-ui/bootstrap.sh`):
```yaml
- bash platform/22-polaris-routes/bootstrap.sh
- bash platform/22-polaris-routes/validate.sh
```

Wave 24 (e2e-validation) and wave 25 (table-maintenance-*) remain outside `bootstrap-by-scripts`, consistent with current behaviour. This design does not add them.

## ArgoCD App-of-Apps Template

**`charts/app-of-apps/templates/22-polaris-routes.yaml`**
```yaml
{{- if and (ge 22 (int .Values.deploy.waveFrom)) (le 22 (int .Values.deploy.waveTo)) }}
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: polaris-routes
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "22"
spec:
  project: {{ .Values.project.name }}
  source:
    repoURL: https://github.com/kuanchoulai10/retail-lakehouse
    targetRevision: main
    path: platform/22-polaris-routes
    directory:
      recurse: false
      include: '{gateway.yaml,polaris-httproute.yaml,backend-httproute.yaml}'
  destination:
    name: {{ .Values.spec.destination.name }}
    namespace: default
  syncPolicy:
    syncOptions:
      - ServerSideApply=true
    automated:
      prune: true
      selfHeal: true
{{- end }}
```

`directory.include` is a glob restricted to the three manifest files, so `bootstrap.sh`, `validate.sh`, and `README.md` are not swept up by the directory sync.

`destination.namespace: default` is the ArgoCD default — actual resources have their own `metadata.namespace` (`istio-ingress` for the Gateway, `polaris` for the HTTPRoutes), so this field only affects any manifests without an explicit namespace (none, in this case).

The template stays inert until `charts/app-of-apps/values.yaml`'s `waveTo` is raised to `>= 22`.

## Manual Test Procedure

```bash
# 1. Start port-forward to Envoy ingress gateway
kubectl port-forward svc/istio-ingressgateway -n istio-ingress 8080:80 \
  --context retail-lakehouse &

# 2. Hit a Polaris endpoint (catchall route)
curl -v http://localhost:8080/api/management/v1/config
# Expected: 200 OK from Polaris

# 3. Hit a backend endpoint (only works after wave 25 backend is deployed to polaris ns)
curl -v http://localhost:8080/v1/jobs
# Expected: 200 OK from table-maintenance-backend

# 4. Hit an unknown path (falls through to catchall)
curl -v http://localhost:8080/foobar
# Expected: 404 from Polaris (its own 404 handler)

# 5. Inspect HTTPRoute status
kubectl get httproutes -n polaris --context retail-lakehouse -o wide
# Expected before wave 25: both Accepted=True; backend-route ResolvedRefs=False
# Expected after wave 25:  both Accepted=True; both ResolvedRefs=True
```

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| `backend-route` HTTPRoute stays `BackendNotFound` indefinitely because wave 25 is never run manually | This is the same behaviour as any other manual-install workflow. Document the port-forward + wave 25 sequence in the README. |
| Backend `/v1/` prefix later renamed | Update `backend-httproute.yaml`'s `matches[0].path.value` in a single-file PR. No other resource is coupled to the prefix. |
| Polaris introduces new `/v1/` endpoints in the future | Gateway API's most-specific match will route those to backend. If Polaris ever ships something under `/v1/`, an explicit rule can be added to `polaris-httproute.yaml` to reclaim the specific path. |
| Existing scheduler pod caches DB DNS name after ns move | Recreate the pod (`kubectl rollout restart deployment/table-maintenance-scheduler -n polaris`) after the yaml changes are applied. This is a one-time migration cost. |
| ArgoCD directory sync includes shell scripts | `include` glob explicitly whitelists the three manifest files. |
| Two HTTPRoutes race on Programmed | Gateway `Programmed` condition covers listener admission and is independent of attached routes. Both HTTPRoutes attach independently and idempotently. |

## Follow-ups (not in this design)

- External exposure: change `istio-ingressgateway` service to `NodePort` or add `minikube tunnel` for LoadBalancer.
- TLS termination on the Gateway (port 443 listener + cert-manager Certificate).
- Ambient-mode enrollment of the `polaris` namespace so pod-to-pod traffic is HBONE-encrypted.
- Prometheus scrape and OTel export for the Envoy ingress metrics.
- `HTTPRoute`/`Gateway` for Trino, Kafka UI, and other cluster services.
- Wiring wave 24 (e2e-validation) and wave 25 (table-maintenance-*) into `bootstrap-by-scripts`.
