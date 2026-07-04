# Istio Ambient Mode — Onboard Design

**Date**: 2026-07-04
**Status**: Draft

## Motivation

Introduce Istio ambient mode as the future service mesh substrate for `retail-lakehouse`. This first cut installs the control plane and dataplane components only — no namespace is enrolled into the mesh yet, and no `Gateway`/`HTTPRoute` resources are created. The purpose is to prove that Istio + Gateway API can be installed cleanly under our platform conventions (`platform/<wave>-<name>/bootstrap.sh` + `validate.sh` + `values.yaml`) and integrated into `task onboard` and the ArgoCD app-of-apps, so that a subsequent iteration can route traffic (e.g., Polaris as default, table-maintenance backend for selected paths) via `HTTPRoute`.

## Scope

**In scope**
- Six new platform directories under `platform/`:
  - `11-istio-base`
  - `11-gateway-api-crds`
  - `12-istiod`
  - `12-istio-cni`
  - `12-ztunnel`
  - `12-istio-ingressgw`
- `tasks/apps.yml` `bootstrap-by-scripts` extended with the new bootstrap/validate calls.
- ArgoCD app-of-apps templates for each new directory under `charts/app-of-apps/templates/`.

**Out of scope (deferred to a later change)**
- `platform/26-platform-routes/` (Gateway + HTTPRoute for Polaris ↔ backend routing).
- Enrolling any namespace into ambient mode (`istio.io/dataplane-mode=ambient` label).
- `istio-csr` cert-manager integration (istiod uses its self-signed CA in this iteration).
- Exposing the ingress gateway externally (service stays `ClusterIP`).
- Prometheus/Otel scrape configuration for Istio metrics.

## Key Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Istio version | `1.26.8` (pinned via `ISTIO_VERSION` env var in each bootstrap.sh) |
| 2 | cert-manager integration | None yet — istiod self-signed CA |
| 3 | Ingress gateway namespace | `istio-ingress` (separate from `istio-system`) |
| 4 | Gateway API install source | `kubectl apply --server-side` against upstream release YAML |
| 5 | Gateway API version | `v1.3.0`, standard channel |
| 6 | ArgoCD sync-wave allocation | Wave 11: `istio-base`, `gateway-api-crds`; Wave 12: `istiod`, `istio-cni`, `ztunnel`, `istio-ingressgw` |
| 7 | Ambient namespace enrollment | None in this change |
| 8 | Ingress gateway `service.type` | `ClusterIP` (no external exposure yet) |
| 9 | Minikube compatibility flag | `global.platform=minikube` applied to istiod, istio-cni, ztunnel values |

## Directory Layout

```
platform/
├── 11-istio-base/
│   ├── bootstrap.sh
│   ├── validate.sh
│   ├── values.yaml
│   └── README.md
├── 11-gateway-api-crds/
│   ├── bootstrap.sh
│   ├── validate.sh
│   └── README.md
├── 12-istiod/
│   ├── bootstrap.sh
│   ├── validate.sh
│   ├── values.yaml
│   └── README.md
├── 12-istio-cni/
│   ├── bootstrap.sh
│   ├── validate.sh
│   ├── values.yaml
│   └── README.md
├── 12-ztunnel/
│   ├── bootstrap.sh
│   ├── validate.sh
│   ├── values.yaml
│   └── README.md
└── 12-istio-ingressgw/
    ├── bootstrap.sh
    ├── validate.sh
    ├── values.yaml
    └── README.md
```

Each directory mirrors the shape of `platform/11-keda/`:
- `bootstrap.sh`: sources `scripts/utils/log.sh`, requires `KUBE_CONTEXT`, pins version via env var, runs `helm upgrade --install` (or `kubectl apply --server-side` for gateway-api-crds), passes `--kube-context "${KUBE_CONTEXT}"`.
- `validate.sh`: sources `scripts/utils/log.sh`, requires `KUBE_CONTEXT`, uses `TIMEOUT` env var (default `300s`), runs `kubectl wait` (for CRDs) or `kubectl rollout status` (for Deployments/DaemonSets).
- `values.yaml`: minimal, only overrides Istio-mandated flags for ambient mode + minikube.
- `README.md`: short header describing what the directory installs and any manual steps.

## Helm Values

### `platform/11-istio-base/values.yaml`
```yaml
defaultRevision: default
```

### `platform/12-istiod/values.yaml`
```yaml
profile: ambient

global:
  platform: minikube

meshConfig:
  accessLogFile: /dev/stdout

pilot:
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      memory: 512Mi
```

### `platform/12-istio-cni/values.yaml`
```yaml
profile: ambient
global:
  platform: minikube
```

### `platform/12-ztunnel/values.yaml`
```yaml
global:
  platform: minikube
```

Note: ztunnel is ambient-only (there is no sidecar variant), so the `profile: ambient` flag used by istiod/cni does not apply.

### `platform/12-istio-ingressgw/values.yaml`
```yaml
service:
  type: ClusterIP
```

## Bootstrap / Validate Scripts

### `platform/11-istio-base/bootstrap.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.8}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "istio-base installed"
log::on_failure "istio-base installation failed"

helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update istio

helm upgrade --install istio-base istio/base \
  --version "${ISTIO_VERSION}" \
  --namespace istio-system --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
```

### `platform/11-istio-base/validate.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "istio-base is ready"
log::on_failure "istio-base is not ready"

for crd in \
  virtualservices.networking.istio.io \
  gateways.networking.istio.io \
  destinationrules.networking.istio.io \
  peerauthentications.security.istio.io \
  authorizationpolicies.security.istio.io; do
  kubectl wait --for=condition=Established "crd/${crd}" \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
done
```

### `platform/11-gateway-api-crds/bootstrap.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
GATEWAY_API_VERSION="${GATEWAY_API_VERSION:-v1.3.0}"

log::on_success "Gateway API CRDs installed"
log::on_failure "Gateway API CRDs installation failed"

kubectl apply --server-side \
  --context "${KUBE_CONTEXT}" \
  -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml"
```

### `platform/11-gateway-api-crds/validate.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Gateway API CRDs are established"
log::on_failure "Gateway API CRDs are not established"

for crd in \
  gatewayclasses.gateway.networking.k8s.io \
  gateways.gateway.networking.k8s.io \
  httproutes.gateway.networking.k8s.io \
  grpcroutes.gateway.networking.k8s.io \
  referencegrants.gateway.networking.k8s.io; do
  kubectl wait --for=condition=Established "crd/${crd}" \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
done
```

### `platform/12-istiod/bootstrap.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.8}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "istiod installed"
log::on_failure "istiod installation failed"

helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update istio

helm upgrade --install istiod istio/istiod \
  --version "${ISTIO_VERSION}" \
  --namespace istio-system --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
```

### `platform/12-istiod/validate.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "istiod is ready"
log::on_failure "istiod is not ready"

kubectl rollout status deployment/istiod \
  --namespace istio-system \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
```

### `platform/12-istio-cni/bootstrap.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.8}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "istio-cni installed"
log::on_failure "istio-cni installation failed"

helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update istio

helm upgrade --install istio-cni istio/cni \
  --version "${ISTIO_VERSION}" \
  --namespace istio-system \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
```

### `platform/12-istio-cni/validate.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "istio-cni is ready"
log::on_failure "istio-cni is not ready"

kubectl rollout status daemonset/istio-cni-node \
  --namespace istio-system \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
```

### `platform/12-ztunnel/bootstrap.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.8}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "ztunnel installed"
log::on_failure "ztunnel installation failed"

helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update istio

helm upgrade --install ztunnel istio/ztunnel \
  --version "${ISTIO_VERSION}" \
  --namespace istio-system \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
```

### `platform/12-ztunnel/validate.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "ztunnel is ready"
log::on_failure "ztunnel is not ready"

kubectl rollout status daemonset/ztunnel \
  --namespace istio-system \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
```

### `platform/12-istio-ingressgw/bootstrap.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.8}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "istio-ingressgateway installed"
log::on_failure "istio-ingressgateway installation failed"

helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update istio

helm upgrade --install istio-ingressgateway istio/gateway \
  --version "${ISTIO_VERSION}" \
  --namespace istio-ingress --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
```

### `platform/12-istio-ingressgw/validate.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "istio-ingressgateway is ready"
log::on_failure "istio-ingressgateway is not ready"

kubectl rollout status deployment/istio-ingressgateway \
  --namespace istio-ingress \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
```

## `tasks/apps.yml` Changes

Extend `bootstrap-by-scripts`:

**`status:` block** — append after the existing `platform/23-trino/validate.sh` line:
```yaml
- TIMEOUT=10s bash platform/11-istio-base/validate.sh
- TIMEOUT=10s bash platform/11-gateway-api-crds/validate.sh
- TIMEOUT=10s bash platform/12-istiod/validate.sh
- TIMEOUT=10s bash platform/12-istio-cni/validate.sh
- TIMEOUT=10s bash platform/12-ztunnel/validate.sh
- TIMEOUT=10s bash platform/12-istio-ingressgw/validate.sh
```

**`cmds:` block** — insert between the existing wave-11 block (after `platform/11-otel-operator/validate.sh`) and the wave-20 block (before `platform/20-kafka-cluster/bootstrap.sh`):
```yaml
- bash platform/11-istio-base/bootstrap.sh
- bash platform/11-gateway-api-crds/bootstrap.sh
- bash platform/11-istio-base/validate.sh
- bash platform/11-gateway-api-crds/validate.sh
- bash platform/12-istiod/bootstrap.sh
- bash platform/12-istiod/validate.sh
- bash platform/12-istio-cni/bootstrap.sh
- bash platform/12-ztunnel/bootstrap.sh
- bash platform/12-istio-ingressgw/bootstrap.sh
- bash platform/12-istio-cni/validate.sh
- bash platform/12-ztunnel/validate.sh
- bash platform/12-istio-ingressgw/validate.sh
```

Rationale: `istiod` is bootstrapped and validated *before* `istio-cni`/`ztunnel`/`istio-ingressgw` because those three components connect to istiod on startup. The three dataplane bootstraps run back-to-back before their validates so that helm installs can proceed in parallel while the DaemonSets/Deployment schedule pods.

## ArgoCD App-of-Apps Templates

For each new platform directory create `charts/app-of-apps/templates/<wave>-<name>.yaml`, mirroring the pattern of `charts/app-of-apps/templates/11-keda.yaml` and its siblings. `waveFrom`/`waveTo` guarding in `values.yaml` continues to gate rendering. The files are:

- `charts/app-of-apps/templates/11-istio-base.yaml` (sync-wave `"11"`)
- `charts/app-of-apps/templates/11-gateway-api-crds.yaml` (sync-wave `"11"`)
- `charts/app-of-apps/templates/12-istiod.yaml` (sync-wave `"12"`)
- `charts/app-of-apps/templates/12-istio-cni.yaml` (sync-wave `"12"`)
- `charts/app-of-apps/templates/12-ztunnel.yaml` (sync-wave `"12"`)
- `charts/app-of-apps/templates/12-istio-ingressgw.yaml` (sync-wave `"12"`)

The exact `Application` spec (repoURL, chart source, targetRevision) mirrors whichever pattern the existing `11-*` templates use (helm chart from upstream repo). `11-gateway-api-crds.yaml` uses a directory/YAML source referencing upstream release manifests. Concrete details defer to implementation time — the plan step will read `11-keda.yaml` and clone the shape.

`charts/app-of-apps/values.yaml` `waveTo: 10` currently gates rendering; it does not need to change for this design (this design does not require enabling ArgoCD-driven Istio deploy — running `bootstrap-by-scripts` will still install everything). If ArgoCD deploy is desired later, bumping `waveTo` to `12` is the only user-facing change.

## Offboard

`task offboard` deletes the minikube cluster and colima VM wholesale, so no per-component uninstall logic is required. Nothing to add for offboard.

## Manual Verification Checklist

After running `task onboard KUBE_CONTEXT=retail-lakehouse DEPLOY_METHOD=scripts` (or the individual `bootstrap.sh` scripts in wave order), the user verifies:

1. Istio system pods are running:
   ```
   kubectl get pods -n istio-system --context retail-lakehouse
   ```
   Expected: `istiod-*` (Running), `istio-cni-node-*` (Running, DaemonSet), `ztunnel-*` (Running, DaemonSet).

2. Ingress gateway pod is running:
   ```
   kubectl get pods -n istio-ingress --context retail-lakehouse
   ```
   Expected: `istio-ingressgateway-*` (Running).

3. CRDs are established:
   ```
   kubectl get crd --context retail-lakehouse | grep -E "istio|gateway.networking"
   ```
   Expected: at least ~25 Istio CRDs + 5 Gateway API CRDs.

4. GatewayClass `istio` is available:
   ```
   kubectl get gatewayclass --context retail-lakehouse
   ```
   Expected: `istio` GatewayClass with `Accepted` status.

5. No sidecars are being injected into existing pods (confirm ambient enrollment is inert until namespaces are labelled):
   ```
   kubectl get pods -A --context retail-lakehouse -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}: {.spec.containers[*].name}{"\n"}{end}' | grep -c istio-proxy
   ```
   Expected: `0`.

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| istio-cni fails to write CNI config on minikube's docker driver | `global.platform=minikube` is set; if it still fails, check `/etc/cni/net.d` inside the minikube node via `minikube ssh` |
| ztunnel cannot reach istiod (chicken-egg) | Bootstrap script installs istiod first and waits for rollout before cni/ztunnel |
| Gateway API CRDs conflict with a future Istio-bundled version | Pinning `GATEWAY_API_VERSION=v1.3.0` and using standard channel keeps CRDs GA-only |
| Wave 11 install order (base before istiod) violated | ArgoCD sync-wave (11 vs 12) enforces this; bootstrap script also enforces via sequential bash |
| Resource pressure on single-node minikube | pilot resources capped; ztunnel/cni are lightweight (~40MB each) |

## Follow-ups (not in this design)

- `platform/26-platform-routes/`: `Gateway` + `HTTPRoute` for Polaris (catch-all) and table-maintenance backend (specific paths).
- Namespace enrollment: label `polaris`, `default`, etc. with `istio.io/dataplane-mode=ambient` when ready.
- `istio-csr` for cert-manager-issued mesh certificates.
- Prometheus ServiceMonitor / OTel export for Istio metrics.
- Bump ArgoCD app-of-apps `waveTo` to 12 to enable Istio via ArgoCD.
- Expose ingress gateway externally (NodePort/LoadBalancer + minikube tunnel).
