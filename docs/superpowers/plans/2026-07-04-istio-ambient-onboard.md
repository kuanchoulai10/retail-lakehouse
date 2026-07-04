# Istio Ambient Onboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add six new `platform/` directories (istio-base, gateway-api-crds, istiod, istio-cni, ztunnel, istio-ingressgw) plus their `tasks/apps.yml` integration and ArgoCD app-of-apps templates, so `task onboard` installs Istio ambient mode + Gateway API CRDs alongside the existing platform.

**Architecture:** Follow the existing `platform/<wave>-<name>/{bootstrap.sh,validate.sh,values.yaml,README.md}` shape. Wave 11 hosts CRD installers (istio-base, gateway-api-crds); wave 12 hosts the control plane (istiod), dataplane (cni, ztunnel), and ingress gateway. `bootstrap-by-scripts` runs istiod before cni/ztunnel/ingressgw so those three can register against a live control plane. No namespace is enrolled in ambient mode by this plan.

**Tech Stack:** Helm (Istio charts `istio/base`, `istio/istiod`, `istio/cni`, `istio/ztunnel`, `istio/gateway`), `kubectl apply --server-side` (Gateway API upstream YAML), Bash, Task, ArgoCD Application (helm/git sources).

## Global Constraints

- Istio charts pinned to `ISTIO_VERSION=1.26.2` (override via env var).
- Gateway API CRDs pinned to `GATEWAY_API_VERSION=v1.3.0`, standard channel.
- Every `bootstrap.sh`/`validate.sh` must `: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"` — no fallback.
- `kubectl` invocations put subcommand first, flags last (e.g. `kubectl rollout status ... --context "${KUBE_CONTEXT}"`, never `kubectl --context ... rollout status`).
- No `cd` in shell scripts; always resolve `SCRIPT_DIR` and use absolute paths / `--values` flags.
- No explanatory comment blocks in `values.yaml` — settings only.
- `values.yaml` overrides only the Istio-mandated flags for ambient + minikube; no other defaults duplicated.
- `global.platform=minikube` set in istiod, istio-cni, ztunnel values (docker-driver bind-mount workaround).
- `profile: ambient` set in istiod and istio-cni values only; ztunnel does not take this flag.
- Istio control plane in namespace `istio-system`; ingress gateway in namespace `istio-ingress` (separate).
- No namespace gets `istio.io/dataplane-mode=ambient` label in this plan.
- Ingress gateway `service.type=ClusterIP` (no external exposure yet).
- Commits: Conventional Commits, scope `platform` or `tasks` or `charts`.

---

## File Structure

**New files (per platform directory):**
```
platform/11-istio-base/{bootstrap.sh,validate.sh,values.yaml,README.md}
platform/11-gateway-api-crds/{bootstrap.sh,validate.sh,README.md}   # no values.yaml
platform/12-istiod/{bootstrap.sh,validate.sh,values.yaml,README.md}
platform/12-istio-cni/{bootstrap.sh,validate.sh,values.yaml,README.md}
platform/12-ztunnel/{bootstrap.sh,validate.sh,values.yaml,README.md}
platform/12-istio-ingressgw/{bootstrap.sh,validate.sh,values.yaml,README.md}
```

**ArgoCD templates (one per platform directory):**
```
charts/app-of-apps/templates/11-istio-base.yaml
charts/app-of-apps/templates/11-gateway-api-crds.yaml
charts/app-of-apps/templates/12-istiod.yaml
charts/app-of-apps/templates/12-istio-cni.yaml
charts/app-of-apps/templates/12-ztunnel.yaml
charts/app-of-apps/templates/12-istio-ingressgw.yaml
```

**Modified files:**
```
tasks/apps.yml   # extend bootstrap-by-scripts `status:` and `cmds:` blocks
```

Each platform directory follows the shape of `platform/11-keda/`. Each ArgoCD template follows the shape of `charts/app-of-apps/templates/11-keda.yaml`. `bootstrap-by-argocd` is NOT modified — this plan focuses on script-based install; ArgoCD templates are added but gated by `charts/app-of-apps/values.yaml` `waveTo: 10`, so they render only when the user chooses to bump the gate later.

---

## Task 1: Create `platform/11-istio-base/`

**Files:**
- Create: `platform/11-istio-base/bootstrap.sh`
- Create: `platform/11-istio-base/validate.sh`
- Create: `platform/11-istio-base/values.yaml`
- Create: `platform/11-istio-base/README.md`

**Interfaces:**
- Produces: helm release `istio-base` in namespace `istio-system`; Istio CRDs (virtualservices, gateways, destinationrules, peerauthentications, authorizationpolicies, ...).
- Consumes: nothing (foundation task).

- [ ] **Step 1: Create the values file**

Write `platform/11-istio-base/values.yaml`:
```yaml
defaultRevision: default
```

- [ ] **Step 2: Create the bootstrap script**

Write `platform/11-istio-base/bootstrap.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.2}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "istio-base installed"
log::on_failure "istio-base installation failed"

helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update istio

helm upgrade --install istio-base istio/base \
  --version "${ISTIO_VERSION}" \
  --namespace istio-system \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
```

Make it executable: `chmod +x platform/11-istio-base/bootstrap.sh`

- [ ] **Step 3: Create the validate script**

Write `platform/11-istio-base/validate.sh`:
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

Make it executable: `chmod +x platform/11-istio-base/validate.sh`

- [ ] **Step 4: Create the README**

Write `platform/11-istio-base/README.md`:
```markdown
# istio-base

Installs Istio's base CRDs and cluster roles into the `istio-system` namespace via the `istio/base` Helm chart. This is the foundation layer — it must be installed before `istiod`, `istio-cni`, or `ztunnel`.

## Deployed Resources

```
Namespace: istio-system
└── (CRDs and ClusterRoles only; no workloads)
```

## Namespaces

- `istio-system` (created)

## CRDs

| CRD | Purpose |
|-----|---------|
| `virtualservices.networking.istio.io` | Layer-7 routing rules |
| `gateways.networking.istio.io` | Ingress/egress traffic entry points |
| `destinationrules.networking.istio.io` | Load balancing, connection pool, TLS settings |
| `peerauthentications.security.istio.io` | Mesh-side mTLS policy |
| `authorizationpolicies.security.istio.io` | Access control between workloads |
| (~20 additional Istio CRDs) | Telemetry, ServiceEntry, Sidecar, WasmPlugin, ProxyConfig, ... |
```

- [ ] **Step 5: Syntax check**

Run: `bash -n platform/11-istio-base/bootstrap.sh && bash -n platform/11-istio-base/validate.sh`
Expected: no output (silent success).

Run: `shellcheck platform/11-istio-base/bootstrap.sh platform/11-istio-base/validate.sh`
Expected: no findings.

- [ ] **Step 6: Commit**

```bash
git add platform/11-istio-base
git commit -m "feat(platform): add 11-istio-base for Istio ambient CRDs"
```

---

## Task 2: Create `platform/11-gateway-api-crds/`

**Files:**
- Create: `platform/11-gateway-api-crds/bootstrap.sh`
- Create: `platform/11-gateway-api-crds/validate.sh`
- Create: `platform/11-gateway-api-crds/README.md`

**Interfaces:**
- Produces: Kubernetes Gateway API standard-channel CRDs (`gatewayclasses`, `gateways`, `httproutes`, `grpcroutes`, `referencegrants`).
- Consumes: nothing.

- [ ] **Step 1: Create the bootstrap script**

Write `platform/11-gateway-api-crds/bootstrap.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
GATEWAY_API_VERSION="${GATEWAY_API_VERSION:-v1.3.0}"

log::on_success "Gateway API CRDs installed"
log::on_failure "Gateway API CRDs installation failed"

kubectl apply --server-side \
  -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml" \
  --context "${KUBE_CONTEXT}"
```

Make it executable: `chmod +x platform/11-gateway-api-crds/bootstrap.sh`

- [ ] **Step 2: Create the validate script**

Write `platform/11-gateway-api-crds/validate.sh`:
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

Make it executable: `chmod +x platform/11-gateway-api-crds/validate.sh`

- [ ] **Step 3: Create the README**

Write `platform/11-gateway-api-crds/README.md`:
```markdown
# gateway-api-crds

Installs the Kubernetes Gateway API standard-channel CRDs via `kubectl apply --server-side` against the upstream release YAML. Pinned to `v1.3.0`, standard channel — GA resources only (no experimental TCPRoute/UDPRoute/TLSRoute).

## Deployed Resources

CRDs only, no namespace, no workloads.

## CRDs

| CRD | Purpose |
|-----|---------|
| `gatewayclasses.gateway.networking.k8s.io` | Declares a controller implementation (e.g. Istio) |
| `gateways.gateway.networking.k8s.io` | Instantiates an inbound listener bound to a GatewayClass |
| `httproutes.gateway.networking.k8s.io` | HTTP L7 routing rules attached to a Gateway |
| `grpcroutes.gateway.networking.k8s.io` | gRPC routing rules attached to a Gateway |
| `referencegrants.gateway.networking.k8s.io` | Cross-namespace reference authorization |
```

- [ ] **Step 4: Syntax check**

Run: `bash -n platform/11-gateway-api-crds/bootstrap.sh && bash -n platform/11-gateway-api-crds/validate.sh`
Expected: no output.

Run: `shellcheck platform/11-gateway-api-crds/bootstrap.sh platform/11-gateway-api-crds/validate.sh`
Expected: no findings.

- [ ] **Step 5: Commit**

```bash
git add platform/11-gateway-api-crds
git commit -m "feat(platform): add 11-gateway-api-crds for Gateway API standard CRDs"
```

---

## Task 3: Create `platform/12-istiod/`

**Files:**
- Create: `platform/12-istiod/bootstrap.sh`
- Create: `platform/12-istiod/validate.sh`
- Create: `platform/12-istiod/values.yaml`
- Create: `platform/12-istiod/README.md`

**Interfaces:**
- Produces: helm release `istiod` in `istio-system`; Deployment `istiod`; xDS control plane on `istiod.istio-system.svc:15012`.
- Consumes: Istio CRDs from Task 1 (must be installed first).

- [ ] **Step 1: Create the values file**

Write `platform/12-istiod/values.yaml`:
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

- [ ] **Step 2: Create the bootstrap script**

Write `platform/12-istiod/bootstrap.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.2}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "istiod installed"
log::on_failure "istiod installation failed"

helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update istio

helm upgrade --install istiod istio/istiod \
  --version "${ISTIO_VERSION}" \
  --namespace istio-system \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
```

Make it executable: `chmod +x platform/12-istiod/bootstrap.sh`

- [ ] **Step 3: Create the validate script**

Write `platform/12-istiod/validate.sh`:
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

Make it executable: `chmod +x platform/12-istiod/validate.sh`

- [ ] **Step 4: Create the README**

Write `platform/12-istiod/README.md`:
```markdown
# istiod

Installs the Istio control plane (istiod) in ambient profile via the `istio/istiod` Helm chart. istiod issues workload certificates and pushes xDS configuration to ztunnel (and future waypoint proxies). Configured with `global.platform=minikube` to work around minikube's non-standard docker-driver bind-mount paths.

## Deployed Resources

```
Namespace: istio-system
└── istiod  (Deployment)
```

## Namespaces

- `istio-system`

## Pods

| Pod | Purpose |
|-----|---------|
| `istiod` | Control plane: config generation, CA, xDS server, sidecar injector webhook |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `istiod` | 15010 | Plaintext xDS (legacy) |
| `istiod` | 15012 | mTLS xDS (used by ztunnel and waypoints) |
| `istiod` | 15014 | Monitoring |
| `istiod` | 15017 | Sidecar-injector webhook |
```

- [ ] **Step 5: Syntax check**

Run: `bash -n platform/12-istiod/bootstrap.sh && bash -n platform/12-istiod/validate.sh`
Expected: no output.

Run: `shellcheck platform/12-istiod/bootstrap.sh platform/12-istiod/validate.sh`
Expected: no findings.

- [ ] **Step 6: Commit**

```bash
git add platform/12-istiod
git commit -m "feat(platform): add 12-istiod ambient control plane"
```

---

## Task 4: Create `platform/12-istio-cni/`

**Files:**
- Create: `platform/12-istio-cni/bootstrap.sh`
- Create: `platform/12-istio-cni/validate.sh`
- Create: `platform/12-istio-cni/values.yaml`
- Create: `platform/12-istio-cni/README.md`

**Interfaces:**
- Produces: helm release `istio-cni` in `istio-system`; DaemonSet `istio-cni-node`.
- Consumes: istiod from Task 3.

- [ ] **Step 1: Create the values file**

Write `platform/12-istio-cni/values.yaml`:
```yaml
profile: ambient

global:
  platform: minikube
```

- [ ] **Step 2: Create the bootstrap script**

Write `platform/12-istio-cni/bootstrap.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.2}"

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

Make it executable: `chmod +x platform/12-istio-cni/bootstrap.sh`

- [ ] **Step 3: Create the validate script**

Write `platform/12-istio-cni/validate.sh`:
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

Make it executable: `chmod +x platform/12-istio-cni/validate.sh`

- [ ] **Step 4: Create the README**

Write `platform/12-istio-cni/README.md`:
```markdown
# istio-cni

Installs the Istio CNI node agent in ambient profile via the `istio/cni` Helm chart. Runs as a DaemonSet on every node and programs the host's iptables/nftables to redirect ambient-mode workload traffic into ztunnel. Requires `global.platform=minikube` to place the CNI binary/config in minikube-compatible directories.

## Deployed Resources

```
Namespace: istio-system
└── istio-cni-node  (DaemonSet, one pod per node)
```

## Namespaces

- `istio-system`

## Pods

| Pod | Purpose |
|-----|---------|
| `istio-cni-node` | CNI plugin installer + node-agent that programs ambient traffic redirection |
```

- [ ] **Step 5: Syntax check**

Run: `bash -n platform/12-istio-cni/bootstrap.sh && bash -n platform/12-istio-cni/validate.sh`
Expected: no output.

Run: `shellcheck platform/12-istio-cni/bootstrap.sh platform/12-istio-cni/validate.sh`
Expected: no findings.

- [ ] **Step 6: Commit**

```bash
git add platform/12-istio-cni
git commit -m "feat(platform): add 12-istio-cni ambient node agent"
```

---

## Task 5: Create `platform/12-ztunnel/`

**Files:**
- Create: `platform/12-ztunnel/bootstrap.sh`
- Create: `platform/12-ztunnel/validate.sh`
- Create: `platform/12-ztunnel/values.yaml`
- Create: `platform/12-ztunnel/README.md`

**Interfaces:**
- Produces: helm release `ztunnel` in `istio-system`; DaemonSet `ztunnel`.
- Consumes: istiod from Task 3 (for xDS + certificates).

- [ ] **Step 1: Create the values file**

Write `platform/12-ztunnel/values.yaml`:
```yaml
global:
  platform: minikube
```

- [ ] **Step 2: Create the bootstrap script**

Write `platform/12-ztunnel/bootstrap.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.2}"

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

Make it executable: `chmod +x platform/12-ztunnel/bootstrap.sh`

- [ ] **Step 3: Create the validate script**

Write `platform/12-ztunnel/validate.sh`:
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

Make it executable: `chmod +x platform/12-ztunnel/validate.sh`

- [ ] **Step 4: Create the README**

Write `platform/12-ztunnel/README.md`:
```markdown
# ztunnel

Installs the Istio ambient L4 proxy (ztunnel) via the `istio/ztunnel` Helm chart. Runs as a DaemonSet on every node and terminates/originates mTLS for ambient-enrolled workloads. `profile: ambient` is not a valid values key for ztunnel (ztunnel is ambient-only), but `global.platform=minikube` is still required for minikube's docker driver.

## Deployed Resources

```
Namespace: istio-system
└── ztunnel  (DaemonSet, one pod per node)
```

## Namespaces

- `istio-system`

## Pods

| Pod | Purpose |
|-----|---------|
| `ztunnel` | Ambient-mode L4 proxy; establishes HBONE mTLS tunnels between nodes |
```

- [ ] **Step 5: Syntax check**

Run: `bash -n platform/12-ztunnel/bootstrap.sh && bash -n platform/12-ztunnel/validate.sh`
Expected: no output.

Run: `shellcheck platform/12-ztunnel/bootstrap.sh platform/12-ztunnel/validate.sh`
Expected: no findings.

- [ ] **Step 6: Commit**

```bash
git add platform/12-ztunnel
git commit -m "feat(platform): add 12-ztunnel ambient L4 dataplane"
```

---

## Task 6: Create `platform/12-istio-ingressgw/`

**Files:**
- Create: `platform/12-istio-ingressgw/bootstrap.sh`
- Create: `platform/12-istio-ingressgw/validate.sh`
- Create: `platform/12-istio-ingressgw/values.yaml`
- Create: `platform/12-istio-ingressgw/README.md`

**Interfaces:**
- Produces: helm release `istio-ingressgateway` in `istio-ingress`; Deployment `istio-ingressgateway`; Service `istio-ingressgateway` (type `ClusterIP`).
- Consumes: istiod from Task 3.

- [ ] **Step 1: Create the values file**

Write `platform/12-istio-ingressgw/values.yaml`:
```yaml
service:
  type: ClusterIP
```

- [ ] **Step 2: Create the bootstrap script**

Write `platform/12-istio-ingressgw/bootstrap.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.2}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "istio-ingressgateway installed"
log::on_failure "istio-ingressgateway installation failed"

helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update istio

helm upgrade --install istio-ingressgateway istio/gateway \
  --version "${ISTIO_VERSION}" \
  --namespace istio-ingress \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
```

Make it executable: `chmod +x platform/12-istio-ingressgw/bootstrap.sh`

- [ ] **Step 3: Create the validate script**

Write `platform/12-istio-ingressgw/validate.sh`:
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

Make it executable: `chmod +x platform/12-istio-ingressgw/validate.sh`

- [ ] **Step 4: Create the README**

Write `platform/12-istio-ingressgw/README.md`:
```markdown
# istio-ingressgw

Installs an Istio ingress gateway (Envoy) via the `istio/gateway` Helm chart into a dedicated `istio-ingress` namespace, isolated from the control plane. Service is `ClusterIP` in this iteration — no external exposure. Future work: attach a `Gateway` + `HTTPRoute` (from `platform/26-platform-routes/`) that terminates HTTP traffic and routes to Polaris (default) and the table-maintenance backend (specific prefixes).

## Deployed Resources

```
Namespace: istio-ingress
├── istio-ingressgateway  (Deployment)
└── istio-ingressgateway  (Service, ClusterIP)
```

## Namespaces

- `istio-ingress` (created; separate from `istio-system` on purpose)

## Pods

| Pod | Purpose |
|-----|---------|
| `istio-ingressgateway` | Envoy proxy that terminates inbound traffic bound to a `Gateway` resource |

## Services

| Service | Type | Port | Purpose |
|---------|------|------|---------|
| `istio-ingressgateway` | ClusterIP | 15021 | Health check |
| `istio-ingressgateway` | ClusterIP | 80 | HTTP inbound |
| `istio-ingressgateway` | ClusterIP | 443 | HTTPS inbound |
```

- [ ] **Step 5: Syntax check**

Run: `bash -n platform/12-istio-ingressgw/bootstrap.sh && bash -n platform/12-istio-ingressgw/validate.sh`
Expected: no output.

Run: `shellcheck platform/12-istio-ingressgw/bootstrap.sh platform/12-istio-ingressgw/validate.sh`
Expected: no findings.

- [ ] **Step 6: Commit**

```bash
git add platform/12-istio-ingressgw
git commit -m "feat(platform): add 12-istio-ingressgw envoy ingress"
```

---

## Task 7: Wire new platforms into `tasks/apps.yml`

**Files:**
- Modify: `tasks/apps.yml` (extend `bootstrap-by-scripts` `status:` and `cmds:` blocks)

**Interfaces:**
- Consumes: bootstrap.sh/validate.sh from Tasks 1-6.
- Produces: `task apps:bootstrap KUBE_CONTEXT=… DEPLOY_METHOD=scripts` installs Istio during wave 11/12.

- [ ] **Step 1: Read current `tasks/apps.yml`**

Run: `sed -n '1,120p' tasks/apps.yml`

Identify:
- The `status:` list under `bootstrap-by-scripts` — find the last existing wave-11 entry (`platform/11-otel-operator/validate.sh` or similar) and the last wave-23 entry.
- The `cmds:` list — find the transition point between wave-11 validate lines and the first wave-20 bootstrap.

- [ ] **Step 2: Extend the `status:` list**

Insert these six lines after the last existing entry in the `status:` list (keeping the file's existing ordering). Any position after the wave-11 entries is fine (idempotency checks are order-independent):

```yaml
    - TIMEOUT=10s bash platform/11-istio-base/validate.sh
    - TIMEOUT=10s bash platform/11-gateway-api-crds/validate.sh
    - TIMEOUT=10s bash platform/12-istiod/validate.sh
    - TIMEOUT=10s bash platform/12-istio-cni/validate.sh
    - TIMEOUT=10s bash platform/12-ztunnel/validate.sh
    - TIMEOUT=10s bash platform/12-istio-ingressgw/validate.sh
```

- [ ] **Step 3: Extend the `cmds:` list**

Insert these lines between the last wave-11 validate (`bash platform/11-otel-operator/validate.sh`) and the first wave-20 bootstrap (`bash platform/20-kafka-cluster/bootstrap.sh`):

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

Ordering rationale: `istio-base` + `gateway-api-crds` produce CRDs that istiod depends on; validate both before continuing. `istiod` bootstraps + validates alone because `istio-cni`, `ztunnel`, and `istio-ingressgw` all connect to it on startup. Those three bootstraps are batched, then their validates run last so pod scheduling happens in parallel.

- [ ] **Step 4: Task parse check**

Run: `task --list`
Expected: task list is printed without a YAML parse error.

Run: `grep "bash platform/1[12]-\(istio\|gateway-api\|ztunnel\)" tasks/apps.yml | wc -l`
Expected: `18` — six new `validate.sh` lines in the `status:` block, plus twelve new `bootstrap.sh`/`validate.sh` lines in the `cmds:` block (6 bootstrap + 6 validate = 12; total 6 + 12 = 18).

- [ ] **Step 5: Commit**

```bash
git add tasks/apps.yml
git commit -m "feat(tasks): wire istio + gateway-api-crds into bootstrap-by-scripts"
```

---

## Task 8: Add ArgoCD app-of-apps templates

**Files:**
- Create: `charts/app-of-apps/templates/11-istio-base.yaml`
- Create: `charts/app-of-apps/templates/11-gateway-api-crds.yaml`
- Create: `charts/app-of-apps/templates/12-istiod.yaml`
- Create: `charts/app-of-apps/templates/12-istio-cni.yaml`
- Create: `charts/app-of-apps/templates/12-ztunnel.yaml`
- Create: `charts/app-of-apps/templates/12-istio-ingressgw.yaml`

**Interfaces:**
- Consumes: platform/ values files created in Tasks 1-6.
- Produces: ArgoCD `Application` resources that install the same Helm releases when the app-of-apps `waveTo` gate is raised to `>= 12`.

Uses the same `Application` shape as `charts/app-of-apps/templates/11-keda.yaml`: `sources[]` with a helm chart repo + a git ref for the values file. `gateway-api-crds` uses a directory source pointing at a git-tracked YAML manifest (not a helm chart), because it is installed via `kubectl apply`.

**One-time preparation for gateway-api-crds:**
The gateway-api-crds ArgoCD Application needs a git-tracked YAML file to sync. Download it once:

- [ ] **Step 1: Vendor the Gateway API standard-install YAML**

Run:
```bash
mkdir -p platform/11-gateway-api-crds/manifests
curl -fsSL \
  -o platform/11-gateway-api-crds/manifests/standard-install-v1.3.0.yaml \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.3.0/standard-install.yaml
```

Verify size > 100KB (real CRD YAML, not an error page):
```bash
wc -c platform/11-gateway-api-crds/manifests/standard-install-v1.3.0.yaml
```
Expected: byte count in the 200000-400000 range.

- [ ] **Step 2: Create `11-istio-base.yaml`**

Write `charts/app-of-apps/templates/11-istio-base.yaml`:
```yaml
{{- if and (ge 11 (int .Values.deploy.waveFrom)) (le 11 (int .Values.deploy.waveTo)) }}
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: istio-base
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "11"
spec:
  project: {{ .Values.project.name }}
  sources:
    - repoURL: https://istio-release.storage.googleapis.com/charts
      chart: base
      targetRevision: 1.26.2
      helm:
        releaseName: istio-base
        valueFiles:
          - '$repo/platform/11-istio-base/values.yaml'
    - repoURL: https://github.com/kuanchoulai10/retail-lakehouse
      targetRevision: main
      ref: repo
  destination:
    name: {{ .Values.spec.destination.name }}
    namespace: istio-system
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
    automated:
      prune: true
      selfHeal: true
{{- end }}
```

- [ ] **Step 3: Create `11-gateway-api-crds.yaml`**

Write `charts/app-of-apps/templates/11-gateway-api-crds.yaml`:
```yaml
{{- if and (ge 11 (int .Values.deploy.waveFrom)) (le 11 (int .Values.deploy.waveTo)) }}
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: gateway-api-crds
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "11"
spec:
  project: {{ .Values.project.name }}
  source:
    repoURL: https://github.com/kuanchoulai10/retail-lakehouse
    targetRevision: main
    path: platform/11-gateway-api-crds/manifests
    directory:
      recurse: false
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

- [ ] **Step 4: Create `12-istiod.yaml`**

Write `charts/app-of-apps/templates/12-istiod.yaml`:
```yaml
{{- if and (ge 12 (int .Values.deploy.waveFrom)) (le 12 (int .Values.deploy.waveTo)) }}
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: istiod
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "12"
spec:
  project: {{ .Values.project.name }}
  sources:
    - repoURL: https://istio-release.storage.googleapis.com/charts
      chart: istiod
      targetRevision: 1.26.2
      helm:
        releaseName: istiod
        valueFiles:
          - '$repo/platform/12-istiod/values.yaml'
    - repoURL: https://github.com/kuanchoulai10/retail-lakehouse
      targetRevision: main
      ref: repo
  destination:
    name: {{ .Values.spec.destination.name }}
    namespace: istio-system
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
    automated:
      prune: true
      selfHeal: true
{{- end }}
```

- [ ] **Step 5: Create `12-istio-cni.yaml`**

Write `charts/app-of-apps/templates/12-istio-cni.yaml`:
```yaml
{{- if and (ge 12 (int .Values.deploy.waveFrom)) (le 12 (int .Values.deploy.waveTo)) }}
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: istio-cni
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "12"
spec:
  project: {{ .Values.project.name }}
  sources:
    - repoURL: https://istio-release.storage.googleapis.com/charts
      chart: cni
      targetRevision: 1.26.2
      helm:
        releaseName: istio-cni
        valueFiles:
          - '$repo/platform/12-istio-cni/values.yaml'
    - repoURL: https://github.com/kuanchoulai10/retail-lakehouse
      targetRevision: main
      ref: repo
  destination:
    name: {{ .Values.spec.destination.name }}
    namespace: istio-system
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
    automated:
      prune: true
      selfHeal: true
{{- end }}
```

- [ ] **Step 6: Create `12-ztunnel.yaml`**

Write `charts/app-of-apps/templates/12-ztunnel.yaml`:
```yaml
{{- if and (ge 12 (int .Values.deploy.waveFrom)) (le 12 (int .Values.deploy.waveTo)) }}
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ztunnel
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "12"
spec:
  project: {{ .Values.project.name }}
  sources:
    - repoURL: https://istio-release.storage.googleapis.com/charts
      chart: ztunnel
      targetRevision: 1.26.2
      helm:
        releaseName: ztunnel
        valueFiles:
          - '$repo/platform/12-ztunnel/values.yaml'
    - repoURL: https://github.com/kuanchoulai10/retail-lakehouse
      targetRevision: main
      ref: repo
  destination:
    name: {{ .Values.spec.destination.name }}
    namespace: istio-system
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
    automated:
      prune: true
      selfHeal: true
{{- end }}
```

- [ ] **Step 7: Create `12-istio-ingressgw.yaml`**

Write `charts/app-of-apps/templates/12-istio-ingressgw.yaml`:
```yaml
{{- if and (ge 12 (int .Values.deploy.waveFrom)) (le 12 (int .Values.deploy.waveTo)) }}
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: istio-ingressgateway
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "12"
spec:
  project: {{ .Values.project.name }}
  sources:
    - repoURL: https://istio-release.storage.googleapis.com/charts
      chart: gateway
      targetRevision: 1.26.2
      helm:
        releaseName: istio-ingressgateway
        valueFiles:
          - '$repo/platform/12-istio-ingressgw/values.yaml'
    - repoURL: https://github.com/kuanchoulai10/retail-lakehouse
      targetRevision: main
      ref: repo
  destination:
    name: {{ .Values.spec.destination.name }}
    namespace: istio-ingress
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
    automated:
      prune: true
      selfHeal: true
{{- end }}
```

- [ ] **Step 8: Render check**

Run: `helm template charts/app-of-apps --set deploy.waveFrom=11 --set deploy.waveTo=12 2>&1 | grep -E "^  name: (istio-base|gateway-api-crds|istiod|istio-cni|ztunnel|istio-ingressgateway)$" | sort -u | wc -l`
Expected: `6` — one line per new Application name renders when the gate is wide. No render errors above the grep.

Run: `helm template charts/app-of-apps 2>&1 | grep -E "^  name: (istio-base|gateway-api-crds|istiod|istio-cni|ztunnel|istio-ingressgateway)$" | wc -l`
Expected: `0` — with the default `waveTo: 10`, the new wave-11/12 gates suppress every new Application, so the file additions are inert until the gate is raised.

- [ ] **Step 9: Commit**

```bash
git add platform/11-gateway-api-crds/manifests charts/app-of-apps/templates
git commit -m "feat(charts): add app-of-apps templates for istio + gateway-api-crds"
```

---

## Post-implementation Manual Verification (user's step)

After all eight tasks are committed, the user runs offboard + onboard manually to prove the wiring works end-to-end. This is NOT part of the plan tasks — it is the user's verification.

1. `task offboard KUBE_CONTEXT=retail-lakehouse` (destroys the cluster)
2. `task onboard KUBE_CONTEXT=retail-lakehouse DEPLOY_METHOD=scripts` (or run the wave-11/12 bootstrap.sh scripts one at a time)
3. Verification:
   ```
   kubectl get pods -n istio-system --context retail-lakehouse
   kubectl get pods -n istio-ingress --context retail-lakehouse
   kubectl get gatewayclass --context retail-lakehouse
   kubectl get crd --context retail-lakehouse | grep -cE "istio|gateway.networking"
   ```
   Expected outcomes match the checklist in the design doc (`docs/superpowers/specs/2026-07-04-istio-ambient-onboard-design.md`, "Manual Verification Checklist" section).

If any bootstrap.sh fails, re-open the relevant task in this plan and iterate.
