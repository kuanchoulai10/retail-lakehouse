# Polaris Routes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add wave-22 `Gateway` + two `HTTPRoute` resources (Polaris catchall + backend under `/v1/`), and move the entire wave-25 `table-maintenance-*` stack (backend, scheduler, db, spark job) from the `default` namespace to `polaris` so HTTPRoutes reference their backends in-namespace.

**Architecture:** One new `platform/22-polaris-routes/` directory holds the Gateway (in `istio-ingress` ns) and both HTTPRoutes (in `polaris` ns). Wave-25 directories keep their existing shape; only namespace fields (and one DB DNS FQDN) change. `bootstrap-by-scripts` gains one new pair of lines; `charts/app-of-apps/templates/` gains one new Application template using a directory source with a glob include.

**Tech Stack:** Kubernetes Gateway API v1 (`gateway.networking.k8s.io/v1`), Istio GatewayClass `istio` (installed by prior spec), `kubectl apply --server-side`, Bash, Task, ArgoCD Application (directory source).

## Global Constraints

- Every `bootstrap.sh`/`validate.sh` must `: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"` — no fallback.
- `kubectl` invocations put subcommand first, flags last (`kubectl apply -f ... --context "${KUBE_CONTEXT}"`, never `kubectl --context ... apply`).
- No `cd` in shell scripts; resolve `SCRIPT_DIR` and use absolute paths.
- No explanatory comment blocks in yaml manifests — settings only.
- Gateway `metadata.namespace: istio-ingress`.
- HTTPRoute `metadata.namespace: polaris` (both routes).
- HTTPRoute `parentRefs[0]`: `{ name: platform-gateway, namespace: istio-ingress }` (both routes).
- Gateway `gatewayClassName: istio`.
- Gateway listener: port 80, protocol HTTP, `allowedRoutes.namespaces.from: Selector`, selector `kubernetes.io/metadata.name: polaris`.
- Backend HTTPRoute path prefix: `/v1/` (with trailing slash).
- Polaris HTTPRoute: catch-all (no `matches` block).
- Wave 22 `validate.sh` waits only for `Programmed` (Gateway) and `Accepted` (both HTTPRoutes), NOT `ResolvedRefs` — the backend Service is legitimately absent at wave 22 time.
- Wave-25 ns migration: `namespace: default` → `polaris`, `--namespace default` → `--namespace polaris`, `.default.svc` → `.polaris.svc`.
- Commits: Conventional Commits, scopes `platform`, `tasks`, or `charts`.

---

## File Structure

**New files:**
```
platform/22-polaris-routes/
├── gateway.yaml
├── polaris-httproute.yaml
├── backend-httproute.yaml
├── bootstrap.sh
├── validate.sh
└── README.md

charts/app-of-apps/templates/22-polaris-routes.yaml
```

**Modified files:**
```
platform/25-tbl-maint-bcknd/backend-deployment.yaml
platform/25-tbl-maint-bcknd/backend-service.yaml
platform/25-tbl-maint-bcknd/backend-rbac.yaml
platform/25-tbl-maint-bcknd/validate.sh
platform/25-tbl-maint-schdlr/scheduler-deployment.yaml
platform/25-tbl-maint-schdlr/validate.sh
platform/25-tbl-maint-db/postgres-deployment.yaml
platform/25-tbl-maint-db/postgres-service.yaml
platform/25-tbl-maint-db/postgres-pvc.yaml
platform/25-tbl-maint-db/validate.sh
platform/25-table-maintenance/sparkapplication-rewrite-data-files.yaml
tasks/apps.yml
```

---

## Task 1: Create `platform/22-polaris-routes/`

**Files:**
- Create: `platform/22-polaris-routes/gateway.yaml`
- Create: `platform/22-polaris-routes/polaris-httproute.yaml`
- Create: `platform/22-polaris-routes/backend-httproute.yaml`
- Create: `platform/22-polaris-routes/bootstrap.sh`
- Create: `platform/22-polaris-routes/validate.sh`
- Create: `platform/22-polaris-routes/README.md`

**Interfaces:**
- Consumes: `Gateway`/`HTTPRoute` CRDs installed by `platform/11-gateway-api-crds/` (from prior spec); `istio` GatewayClass installed by `platform/12-istiod/`; `polaris` namespace created by `platform/21-polaris/`.
- Produces: `Gateway` `istio-ingress/platform-gateway`; `HTTPRoute` `polaris/polaris-catchall`; `HTTPRoute` `polaris/backend-route`. Wave-22 `bootstrap.sh` and `validate.sh` runnable via `KUBE_CONTEXT=… bash platform/22-polaris-routes/…`.

- [ ] **Step 1: Create the Gateway manifest**

Write `platform/22-polaris-routes/gateway.yaml`:
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

- [ ] **Step 2: Create the Polaris catchall HTTPRoute**

Write `platform/22-polaris-routes/polaris-httproute.yaml`:
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

- [ ] **Step 3: Create the backend HTTPRoute**

Write `platform/22-polaris-routes/backend-httproute.yaml`:
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

- [ ] **Step 4: Create the bootstrap script**

Write `platform/22-polaris-routes/bootstrap.sh`:
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

Make it executable: `chmod +x platform/22-polaris-routes/bootstrap.sh`

- [ ] **Step 5: Create the validate script**

Write `platform/22-polaris-routes/validate.sh`:
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

Make it executable: `chmod +x platform/22-polaris-routes/validate.sh`

- [ ] **Step 6: Create the README**

Write `platform/22-polaris-routes/README.md`:
```markdown
# polaris-routes

Installs the north-south routing layer for Polaris + table-maintenance-backend via a single Envoy-backed `Gateway` and two `HTTPRoute`s. External clients hit the ingress on port 80; requests matching `/v1/*` reach the table-maintenance backend, and everything else falls through to Polaris.

Service-to-service (east-west) traffic — for example the backend calling Polaris — does NOT go through this Gateway. In-cluster consumers use Service DNS directly (e.g. `polaris.polaris.svc.cluster.local:8181`).

## Deployed Resources

```
Namespace: istio-ingress
└── platform-gateway  (Gateway)

Namespace: polaris
├── polaris-catchall  (HTTPRoute, catch-all → polaris:8181)
└── backend-route     (HTTPRoute, /v1/ → table-maintenance-backend:8000)
```

## Namespaces

- `istio-ingress` (Gateway, existing — created by `12-istio-ingressgw`)
- `polaris` (HTTPRoutes, existing — created by `21-polaris`)

## Access

The ingress gateway `Service` is `ClusterIP`. To reach it from a laptop:
`kubectl port-forward svc/istio-ingressgateway -n istio-ingress 8080:80 --context <ctx>`
```

- [ ] **Step 7: Syntax check the shell scripts**

Run: `bash -n platform/22-polaris-routes/bootstrap.sh && bash -n platform/22-polaris-routes/validate.sh`
Expected: no output.

Run: `shellcheck platform/22-polaris-routes/bootstrap.sh platform/22-polaris-routes/validate.sh`
Expected: no findings.

- [ ] **Step 8: YAML sanity check**

Run: `kubectl apply --dry-run=client -f platform/22-polaris-routes/gateway.yaml -f platform/22-polaris-routes/polaris-httproute.yaml -f platform/22-polaris-routes/backend-httproute.yaml --context retail-lakehouse 2>&1 | head -20`
Expected: three lines like `gateway.gateway.networking.k8s.io/platform-gateway created (dry run)` / `httproute.gateway.networking.k8s.io/polaris-catchall created (dry run)` / `httproute.gateway.networking.k8s.io/backend-route created (dry run)`. No schema error above.

If the cluster is not running, skip this step and rely on step 7. Note in the commit message if skipped.

- [ ] **Step 9: Commit**

```bash
git add platform/22-polaris-routes
git commit -m "feat(platform): add 22-polaris-routes Gateway + two HTTPRoutes"
```

---

## Task 2: Move wave-25 stack from `default` to `polaris` namespace

**Files:**
- Modify: `platform/25-tbl-maint-bcknd/backend-deployment.yaml`
- Modify: `platform/25-tbl-maint-bcknd/backend-service.yaml`
- Modify: `platform/25-tbl-maint-bcknd/backend-rbac.yaml`
- Modify: `platform/25-tbl-maint-bcknd/validate.sh`
- Modify: `platform/25-tbl-maint-schdlr/scheduler-deployment.yaml`
- Modify: `platform/25-tbl-maint-schdlr/validate.sh`
- Modify: `platform/25-tbl-maint-db/postgres-deployment.yaml`
- Modify: `platform/25-tbl-maint-db/postgres-service.yaml`
- Modify: `platform/25-tbl-maint-db/postgres-pvc.yaml`
- Modify: `platform/25-tbl-maint-db/validate.sh`
- Modify: `platform/25-table-maintenance/sparkapplication-rewrite-data-files.yaml`

**Interfaces:**
- Consumes: `polaris` namespace (created by `platform/21-polaris/`).
- Produces: All eleven files now target the `polaris` namespace so wave-22 HTTPRoutes can resolve them in-namespace without `ReferenceGrant`. Backend `GLAC_POSTGRES__DB_URL` and scheduler `GLAC_POSTGRES__DB_URL` env vars now point at `tbl-maint-db.polaris.svc`.

- [ ] **Step 1: Verify starting state**

Run: `grep -c "default" platform/25-tbl-maint-bcknd/*.yaml platform/25-tbl-maint-bcknd/validate.sh platform/25-tbl-maint-schdlr/*.yaml platform/25-tbl-maint-schdlr/validate.sh platform/25-tbl-maint-db/*.yaml platform/25-tbl-maint-db/validate.sh platform/25-table-maintenance/sparkapplication-rewrite-data-files.yaml`
Expected: a per-file count of the string `default`. Note the totals so step 8 can confirm they drop to zero.

- [ ] **Step 2: Migrate `platform/25-tbl-maint-bcknd/`**

Run:
```bash
sed -i '' \
  -e 's/namespace: default/namespace: polaris/g' \
  -e 's/tbl-maint-db\.default\.svc/tbl-maint-db.polaris.svc/g' \
  platform/25-tbl-maint-bcknd/backend-deployment.yaml \
  platform/25-tbl-maint-bcknd/backend-service.yaml \
  platform/25-tbl-maint-bcknd/backend-rbac.yaml

sed -i '' 's/--namespace default/--namespace polaris/g' \
  platform/25-tbl-maint-bcknd/validate.sh
```

Verify:
```bash
grep -c "default" platform/25-tbl-maint-bcknd/*.yaml platform/25-tbl-maint-bcknd/validate.sh
```
Expected: all counts are `0`.

- [ ] **Step 3: Migrate `platform/25-tbl-maint-schdlr/`**

Run:
```bash
sed -i '' \
  -e 's/namespace: default/namespace: polaris/g' \
  -e 's/tbl-maint-db\.default\.svc/tbl-maint-db.polaris.svc/g' \
  platform/25-tbl-maint-schdlr/scheduler-deployment.yaml

sed -i '' 's/--namespace default/--namespace polaris/g' \
  platform/25-tbl-maint-schdlr/validate.sh
```

Verify:
```bash
grep -c "default" platform/25-tbl-maint-schdlr/scheduler-deployment.yaml platform/25-tbl-maint-schdlr/validate.sh
```
Expected: both counts are `0`.

- [ ] **Step 4: Migrate `platform/25-tbl-maint-db/`**

Run:
```bash
sed -i '' 's/namespace: default/namespace: polaris/g' \
  platform/25-tbl-maint-db/postgres-deployment.yaml \
  platform/25-tbl-maint-db/postgres-service.yaml \
  platform/25-tbl-maint-db/postgres-pvc.yaml

sed -i '' 's/--namespace default/--namespace polaris/g' \
  platform/25-tbl-maint-db/validate.sh
```

Verify:
```bash
grep -c "default" platform/25-tbl-maint-db/*.yaml platform/25-tbl-maint-db/validate.sh
```
Expected: all counts are `0`.

- [ ] **Step 5: Migrate `platform/25-table-maintenance/`**

Run:
```bash
sed -i '' 's/namespace: default/namespace: polaris/g' \
  platform/25-table-maintenance/sparkapplication-rewrite-data-files.yaml
```

Verify:
```bash
grep -c "default" platform/25-table-maintenance/sparkapplication-rewrite-data-files.yaml
```
Expected: `0`.

- [ ] **Step 6: Repo-wide leftover check**

Run:
```bash
grep -rn "namespace: default\|--namespace default\|\.default\.svc" \
  platform/25-tbl-maint-bcknd platform/25-tbl-maint-schdlr platform/25-tbl-maint-db platform/25-table-maintenance
```
Expected: no output (all references migrated).

- [ ] **Step 7: Shell script syntax check**

Run:
```bash
bash -n platform/25-tbl-maint-bcknd/validate.sh
bash -n platform/25-tbl-maint-schdlr/validate.sh
bash -n platform/25-tbl-maint-db/validate.sh
shellcheck platform/25-tbl-maint-bcknd/validate.sh \
  platform/25-tbl-maint-schdlr/validate.sh \
  platform/25-tbl-maint-db/validate.sh
```
Expected: no output from `bash -n`; no findings from `shellcheck`.

- [ ] **Step 8: YAML sanity check**

Run: `kubectl apply --dry-run=client -f platform/25-tbl-maint-bcknd/backend-deployment.yaml -f platform/25-tbl-maint-bcknd/backend-service.yaml -f platform/25-tbl-maint-bcknd/backend-rbac.yaml -f platform/25-tbl-maint-schdlr/scheduler-deployment.yaml -f platform/25-tbl-maint-db/postgres-deployment.yaml -f platform/25-tbl-maint-db/postgres-service.yaml -f platform/25-tbl-maint-db/postgres-pvc.yaml -f platform/25-table-maintenance/sparkapplication-rewrite-data-files.yaml --context retail-lakehouse 2>&1 | head -20`
Expected: eight `created (dry run)` lines, all showing the new namespace (`namespace/name`) with polaris where applicable. If the cluster is not running, skip and rely on step 6.

- [ ] **Step 9: Commit**

```bash
git add platform/25-tbl-maint-bcknd platform/25-tbl-maint-schdlr platform/25-tbl-maint-db platform/25-table-maintenance
git commit -m "refactor(platform): move table-maintenance stack from default to polaris ns"
```

---

## Task 3: Wire `platform/22-polaris-routes/` into `tasks/apps.yml`

**Files:**
- Modify: `tasks/apps.yml` (extend `bootstrap-by-scripts` `status:` and `cmds:` blocks)

**Interfaces:**
- Consumes: `bootstrap.sh`/`validate.sh` from Task 1.
- Produces: `task apps:bootstrap KUBE_CONTEXT=… DEPLOY_METHOD=scripts` runs `platform/22-polaris-routes/` right after `platform/22-kafka-iceberg-connector/`.

- [ ] **Step 1: Read current `tasks/apps.yml`**

Run: `sed -n '46,102p' tasks/apps.yml`

Identify:
- The last entry in `status:` (should be `platform/23-trino/validate.sh` or later, after prior specs added wave-11/12).
- The line in `cmds:` currently reading `bash platform/22-kafka-iceberg-connector/validate.sh`.

- [ ] **Step 2: Extend the `status:` list**

Append the following line at the end of the `status:` block for `bootstrap-by-scripts` (append after the last existing `TIMEOUT=10s bash ...` entry):

```yaml
    - TIMEOUT=10s bash platform/22-polaris-routes/validate.sh
```

- [ ] **Step 3: Extend the `cmds:` list**

Insert these two lines between `bash platform/22-kafka-iceberg-connector/validate.sh` and `bash platform/23-kafka-ui/bootstrap.sh`:

```yaml
      - bash platform/22-polaris-routes/bootstrap.sh
      - bash platform/22-polaris-routes/validate.sh
```

- [ ] **Step 4: Task parse check**

Run: `task --list`
Expected: task list printed without a YAML parse error.

Run: `grep -c "platform/22-polaris-routes" tasks/apps.yml`
Expected: `3` (one status line + one bootstrap line + one validate line in cmds).

- [ ] **Step 5: Commit**

```bash
git add tasks/apps.yml
git commit -m "feat(tasks): wire 22-polaris-routes into bootstrap-by-scripts"
```

---

## Task 4: Add ArgoCD app-of-apps template for `22-polaris-routes`

**Files:**
- Create: `charts/app-of-apps/templates/22-polaris-routes.yaml`

**Interfaces:**
- Consumes: manifests created in Task 1 under `platform/22-polaris-routes/`.
- Produces: ArgoCD `Application` `polaris-routes` (in `argocd` ns) that syncs the three YAML manifests once `charts/app-of-apps/values.yaml`'s `waveTo` is raised to `>= 22`.

- [ ] **Step 1: Create the Application template**

Write `charts/app-of-apps/templates/22-polaris-routes.yaml`:
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

- [ ] **Step 2: Render check with the gate open**

Run: `helm template charts/app-of-apps --set deploy.waveFrom=22 --set deploy.waveTo=22 2>&1 | grep -E "^  name: polaris-routes$" | wc -l`
Expected: `1`.

- [ ] **Step 3: Render check with the default gate closed**

Run: `helm template charts/app-of-apps 2>&1 | grep -E "^  name: polaris-routes$" | wc -l`
Expected: `0` — the default `waveTo` in `charts/app-of-apps/values.yaml` is `10`, so the new template is gated out until the operator explicitly raises the gate.

- [ ] **Step 4: Confirm the include glob is respected**

Run: `helm template charts/app-of-apps --set deploy.waveFrom=22 --set deploy.waveTo=22 2>&1 | grep -E "include:" `
Expected: one line printing the glob `'{gateway.yaml,polaris-httproute.yaml,backend-httproute.yaml}'`. Confirms `bootstrap.sh`/`validate.sh`/`README.md` are not swept up.

- [ ] **Step 5: Commit**

```bash
git add charts/app-of-apps/templates/22-polaris-routes.yaml
git commit -m "feat(charts): add app-of-apps template for 22-polaris-routes"
```

---

## Post-implementation Manual Verification (user's step)

After all four tasks are committed, the user verifies end-to-end on a live cluster (assumes wave 10-12 already up from the prior spec):

1. Apply the new wave 22:
   ```bash
   KUBE_CONTEXT=retail-lakehouse bash platform/22-polaris-routes/bootstrap.sh
   KUBE_CONTEXT=retail-lakehouse bash platform/22-polaris-routes/validate.sh
   ```
   Expected: bootstrap prints three `applied` lines; validate prints three green lines.

2. Confirm Gateway is Programmed and Routes are Accepted:
   ```bash
   kubectl get gateway platform-gateway -n istio-ingress --context retail-lakehouse -o yaml | grep -A2 conditions:
   kubectl get httproutes -n polaris --context retail-lakehouse -o wide
   ```
   Expected: Gateway `Programmed: True`; both HTTPRoutes `Accepted: True`. `backend-route` may show `ResolvedRefs: False` with reason `BackendNotFound` until wave 25 runs — this is expected.

3. Manually apply wave 25 (backend stack now targets `polaris` ns):
   ```bash
   KUBE_CONTEXT=retail-lakehouse bash platform/25-tbl-maint-db/bootstrap.sh
   KUBE_CONTEXT=retail-lakehouse bash platform/25-tbl-maint-bcknd/bootstrap.sh
   KUBE_CONTEXT=retail-lakehouse bash platform/25-tbl-maint-schdlr/bootstrap.sh
   ```
   (Assumes each wave-25 directory already has a `bootstrap.sh`. If not, apply the yaml files with `kubectl apply -f <file> --context retail-lakehouse`.)

4. Confirm the backend Service now exists in `polaris`:
   ```bash
   kubectl get svc table-maintenance-backend -n polaris --context retail-lakehouse
   ```
   Expected: one Service on port 8000.

5. Re-check the backend HTTPRoute:
   ```bash
   kubectl get httproute backend-route -n polaris --context retail-lakehouse -o yaml | grep -A5 conditions:
   ```
   Expected: `Accepted: True` and `ResolvedRefs: True`.

6. Port-forward + curl:
   ```bash
   kubectl port-forward svc/istio-ingressgateway -n istio-ingress 8080:80 --context retail-lakehouse &
   curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:8080/api/management/v1/config
   curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:8080/v1/jobs
   curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:8080/foobar
   ```
   Expected: `200` for the Polaris config, `200` (or backend's real code) for `/v1/jobs`, and Polaris's own `404` for the unknown path.

If any bootstrap fails, re-open the relevant task in this plan.
