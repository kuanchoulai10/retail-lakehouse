# Polaris PostgreSQL Backing Store — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy PostgreSQL into the `polaris` namespace as a durable backing store for Apache Polaris catalog metadata, then switch `21-polaris/` from `in-memory` to `relational-jdbc` persistence and add the corresponding ArgoCD app-of-apps template.

**Architecture:** New sibling component `20-polaris-db/` (sync wave 20) with plain manifests (Secret, PVC, Deployment, Service) + install/uninstall/validate scripts. A single shared Secret named `polaris-db` is the source of truth for credentials and JDBC URL — both the postgres Deployment (via `secretKeyRef`) and the Polaris Helm chart (via `persistence.relationalJdbc.secret`) read from it. `21-polaris/values.yaml` is updated to reference this Secret.

**Tech Stack:** PostgreSQL 17, Kubernetes (Deployment + PVC + Service), Apache Polaris 1.3.0 Helm chart, ArgoCD app-of-apps, kubectl, bash scripts.

**Spec:** `docs/superpowers/specs/2026-04-29-polaris-db-design.md`

---

## File Map

```
20-polaris-db/                              (NEW directory)
├── README.md
├── polaris-db-secret.yaml                  (Secret: username/password/database/jdbcUrl)
├── polaris-db-pvc.yaml                     (5Gi RWO)
├── polaris-db-deployment.yaml              (postgres:17-alpine, secretKeyRef for creds)
├── polaris-db-service.yaml                 (ClusterIP :5432)
├── install.sh                              (apply Secret → PVC → Deployment → Service)
├── uninstall.sh                            (reverse delete; PVC retained)
└── validate.sh                             (wait Ready + pg_isready)

21-polaris/                                 (MODIFY)
├── values.yaml                             (persistence.type: relational-jdbc)
└── README.md                               (Configuration Notes + Sync Wave + smoke test)

charts/app-of-apps/templates/               (MODIFY — add file)
└── 20-polaris-db.yaml                      (ArgoCD Application, sync-wave: 20)
```

---

### Task 1: Create `20-polaris-db/` Kubernetes manifests

**Files:**
- Create: `20-polaris-db/polaris-db-secret.yaml`
- Create: `20-polaris-db/polaris-db-pvc.yaml`
- Create: `20-polaris-db/polaris-db-deployment.yaml`
- Create: `20-polaris-db/polaris-db-service.yaml`

- [ ] **Step 1: Create Secret manifest**

```yaml
# 20-polaris-db/polaris-db-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: polaris-db
  namespace: polaris
  labels:
    app: polaris-db
type: Opaque
stringData:
  username: polaris
  password: polaris
  database: polaris
  jdbcUrl: jdbc:postgresql://polaris-db.polaris.svc.cluster.local:5432/polaris
```

- [ ] **Step 2: Create PVC manifest**

```yaml
# 20-polaris-db/polaris-db-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: polaris-db
  namespace: polaris
  labels:
    app: polaris-db
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

- [ ] **Step 3: Create Deployment manifest**

```yaml
# 20-polaris-db/polaris-db-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: polaris-db
  namespace: polaris
  labels:
    app: polaris-db
spec:
  replicas: 1
  selector:
    matchLabels:
      app: polaris-db
  template:
    metadata:
      labels:
        app: polaris-db
    spec:
      containers:
        - name: postgres
          image: postgres:17-alpine
          env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: polaris-db
                  key: username
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: polaris-db
                  key: password
            - name: POSTGRES_DB
              valueFrom:
                secretKeyRef:
                  name: polaris-db
                  key: database
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          ports:
            - name: postgres
              containerPort: 5432
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
          # NOTE: Probe args duplicate Secret values (probes can't read Secrets).
          # If username/database in the Secret change, update these args in lockstep.
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "polaris", "-d", "polaris"]
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            exec:
              command: ["pg_isready", "-U", "polaris", "-d", "polaris"]
            initialDelaySeconds: 15
            periodSeconds: 10
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: polaris-db
```

- [ ] **Step 4: Create Service manifest**

```yaml
# 20-polaris-db/polaris-db-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: polaris-db
  namespace: polaris
  labels:
    app: polaris-db
spec:
  selector:
    app: polaris-db
  ports:
    - name: postgres
      port: 5432
      targetPort: postgres
```

- [ ] **Step 5: Validate manifest syntax via server-side dry-run**

The `polaris` namespace already exists (deployed by `21-polaris/install.sh` previously) or will be created by `install.sh` in Task 2. For dry-run validation, create the namespace first if absent:

```bash
kubectl create namespace polaris --dry-run=client -o yaml \
  | kubectl apply -f - --context mini

kubectl apply --dry-run=server \
  -f 20-polaris-db/polaris-db-secret.yaml \
  -f 20-polaris-db/polaris-db-pvc.yaml \
  -f 20-polaris-db/polaris-db-deployment.yaml \
  -f 20-polaris-db/polaris-db-service.yaml \
  --context mini
```

Expected output (each line):
```
secret/polaris-db created (server dry run)
persistentvolumeclaim/polaris-db created (server dry run)
deployment.apps/polaris-db created (server dry run)
service/polaris-db created (server dry run)
```

If any line shows an error, fix the manifest and re-run.

- [ ] **Step 6: Commit**

```bash
git add 20-polaris-db/polaris-db-secret.yaml \
        20-polaris-db/polaris-db-pvc.yaml \
        20-polaris-db/polaris-db-deployment.yaml \
        20-polaris-db/polaris-db-service.yaml
git commit -m "feat(polaris-db): add PostgreSQL Kubernetes manifests"
```

---

### Task 2: Create install/uninstall/validate scripts

**Files:**
- Create: `20-polaris-db/install.sh`
- Create: `20-polaris-db/uninstall.sh`
- Create: `20-polaris-db/validate.sh`

- [ ] **Step 1: Create install.sh**

```bash
#!/usr/bin/env bash
# 20-polaris-db/install.sh
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying PostgreSQL for Polaris (context: ${KUBE_CONTEXT})"

# Create namespace if not exists (idempotent)
kubectl create namespace polaris --dry-run=client -o yaml \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

# Apply in order: Secret first (Deployment depends on it via secretKeyRef)
kubectl apply -f "$SCRIPT_DIR/polaris-db-secret.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/polaris-db-pvc.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/polaris-db-deployment.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/polaris-db-service.yaml" --context "${KUBE_CONTEXT}"

echo "==> Done."
```

- [ ] **Step 2: Create uninstall.sh**

```bash
#!/usr/bin/env bash
# 20-polaris-db/uninstall.sh
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Uninstalling PostgreSQL for Polaris (context: ${KUBE_CONTEXT})"
echo "    NOTE: PVC 'polaris-db' is intentionally NOT deleted to prevent data loss."
echo "    To remove data: kubectl delete pvc polaris-db -n polaris --context ${KUBE_CONTEXT}"

kubectl delete -f "$SCRIPT_DIR/polaris-db-service.yaml" \
  --context "${KUBE_CONTEXT}" --ignore-not-found
kubectl delete -f "$SCRIPT_DIR/polaris-db-deployment.yaml" \
  --context "${KUBE_CONTEXT}" --ignore-not-found
kubectl delete -f "$SCRIPT_DIR/polaris-db-secret.yaml" \
  --context "${KUBE_CONTEXT}" --ignore-not-found

echo "==> Done."
```

- [ ] **Step 3: Create validate.sh**

```bash
#!/usr/bin/env bash
# 20-polaris-db/validate.sh
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating PostgreSQL for Polaris (context: ${KUBE_CONTEXT})"

kubectl wait pod \
  -l app=polaris-db \
  -n polaris \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

echo "==> Verifying PostgreSQL is accepting connections..."
POD=$(kubectl get pod -l app=polaris-db -n polaris \
  --context "${KUBE_CONTEXT}" -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n polaris "$POD" --context "${KUBE_CONTEXT}" \
  -- pg_isready -U polaris -d polaris

echo "==> PostgreSQL is ready."
```

- [ ] **Step 4: Make scripts executable**

```bash
chmod +x 20-polaris-db/install.sh 20-polaris-db/uninstall.sh 20-polaris-db/validate.sh
```

- [ ] **Step 5: Lint scripts with shellcheck**

```bash
shellcheck 20-polaris-db/install.sh 20-polaris-db/uninstall.sh 20-polaris-db/validate.sh
```

Expected: no output (all clean). The repo's pre-commit hook also runs shellcheck on commit.

- [ ] **Step 6: Smoke-test scripts (deploy → validate)**

This is the first end-to-end exercise of the new component. It requires the `mini` kubectl context to be available.

```bash
bash 20-polaris-db/install.sh
bash 20-polaris-db/validate.sh
```

Expected final line: `==> PostgreSQL is ready.`

If the pod fails to become Ready, inspect:
```bash
kubectl describe pod -l app=polaris-db -n polaris --context mini
kubectl logs -l app=polaris-db -n polaris --context mini --tail=100
```

Common failure: PVC stuck in `Pending` if no default StorageClass — fix by ensuring minikube has the `standard` StorageClass.

- [ ] **Step 7: Commit**

```bash
git add 20-polaris-db/install.sh 20-polaris-db/uninstall.sh 20-polaris-db/validate.sh
git commit -m "feat(polaris-db): add install/uninstall/validate scripts"
```

---

### Task 3: Create `20-polaris-db/README.md`

**Files:**
- Create: `20-polaris-db/README.md`

- [ ] **Step 1: Create README**

````markdown
# Polaris PostgreSQL

Deploys PostgreSQL 17 as the persistent backing store for Apache Polaris catalog metadata, into the `polaris` namespace. Polaris connects via JDBC and auto-bootstraps its schema on first start.

## Deployed Resources

```
Namespace: polaris
├── polaris-db                            (Deployment)
├── polaris-db                            (Service, port 5432)
├── polaris-db                            (PersistentVolumeClaim, 5Gi)
└── polaris-db                            (Secret: username/password/database/jdbcUrl)
```

## Namespaces

- `polaris` (shared with `21-polaris/`; created by whichever component is installed first)

## Pods

| Pod | Purpose |
|-----|---------|
| `polaris-db` | PostgreSQL 17 storing Polaris catalog metadata (namespaces, tables, principals, schemas) |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `polaris-db.polaris.svc.cluster.local` | 5432 | PostgreSQL connection endpoint |

## Sync Wave

Wave 20 — deploys in parallel with MinIO (also wave 20). Polaris (wave 21) depends on both.

## Connection Info

The Secret `polaris-db` in namespace `polaris` is the single source of truth for connection details. It exposes four keys:

| Key | Value |
|-----|-------|
| `username` | `polaris` |
| `password` | `polaris` |
| `database` | `polaris` |
| `jdbcUrl` | `jdbc:postgresql://polaris-db.polaris.svc.cluster.local:5432/polaris` |

The PostgreSQL Deployment reads `username`/`password`/`database` via `secretKeyRef`. The Polaris Helm chart (`21-polaris/values.yaml`) reads `username`/`password`/`jdbcUrl` via `persistence.relationalJdbc.secret`.

## Schema

Polaris bootstraps its own schema on first connection. No init container or migration tool is required.

## Installation

```bash
bash 20-polaris-db/install.sh
```

## Uninstallation

```bash
bash 20-polaris-db/uninstall.sh
```

The PVC is intentionally retained on uninstall to prevent accidental data loss. Remove it manually if desired:

```bash
kubectl delete pvc polaris-db -n polaris --context mini
```

## Validation

```bash
bash 20-polaris-db/validate.sh
```

## Inspecting Catalog Tables

After Polaris has connected at least once, you can inspect the bootstrapped tables directly:

```bash
POD=$(kubectl get pod -l app=polaris-db -n polaris -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n polaris "$POD" -- psql -U polaris -d polaris -c '\dt'
```
````

- [ ] **Step 2: Commit**

```bash
git add 20-polaris-db/README.md
git commit -m "docs(polaris-db): add README"
```

---

### Task 4: Add ArgoCD app-of-apps template for `20-polaris-db`

**Files:**
- Create: `charts/app-of-apps/templates/20-polaris-db.yaml`

- [ ] **Step 1: Create the template**

```yaml
# charts/app-of-apps/templates/20-polaris-db.yaml
{{- if and (ge 20 (int .Values.deploy.waveFrom)) (le 20 (int .Values.deploy.waveTo)) }}
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: polaris-db
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "20"
spec:
  project: {{ .Values.project.name }}
  sources:
    - repoURL: https://github.com/kuanchoulai10/retail-lakehouse
      path: 20-polaris-db
      targetRevision: main
  destination:
    name: {{ .Values.spec.destination.name }}
    namespace: polaris
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
    automated:
      prune: true
      selfHeal: true
{{- end }}
```

- [ ] **Step 2: Validate Helm template renders**

Render the app-of-apps chart with a wave range that includes 20:

```bash
helm template retail-lakehouse charts/app-of-apps \
  --set deploy.waveFrom=9 \
  --set deploy.waveTo=30 \
  | grep -A1 "name: polaris-db"
```

Expected: shows the rendered ArgoCD `Application` named `polaris-db` with `sync-wave: "20"`.

- [ ] **Step 3: Verify wave-range gating works**

Render with a range that excludes 20:

```bash
helm template retail-lakehouse charts/app-of-apps \
  --set deploy.waveFrom=21 \
  --set deploy.waveTo=30 \
  | grep -c "name: polaris-db" || true
```

Expected: `0` (the conditional block is suppressed).

- [ ] **Step 4: Commit**

```bash
git add charts/app-of-apps/templates/20-polaris-db.yaml
git commit -m "feat(argocd): add polaris-db app-of-apps template"
```

---

### Task 5: Switch `21-polaris/values.yaml` to `relational-jdbc`

**Files:**
- Modify: `21-polaris/values.yaml`

- [ ] **Step 1: Replace the `persistence` block**

Find this block in `21-polaris/values.yaml` (around lines 12-14):

```yaml
  persistence:
    type: in-memory
```

Replace with:

```yaml
  persistence:
    type: relational-jdbc
    relationalJdbc:
      # The Secret 'polaris-db' is created by 20-polaris-db/ in the same namespace.
      # It exposes 'username', 'password', and 'jdbcUrl' keys.
      secret:
        name: polaris-db
        username: username
        password: password
        jdbcUrl: jdbcUrl
```

- [ ] **Step 2: Validate the wrapper Helm chart still renders**

```bash
helm template polaris 21-polaris \
  --namespace polaris \
  --values 21-polaris/values.yaml \
  > /tmp/polaris-rendered.yaml
```

Expected: command exits 0 and `/tmp/polaris-rendered.yaml` contains a populated YAML stream (Deployment, Service, ConfigMap, etc.).

- [ ] **Step 3: Confirm the Secret reference is wired through**

```bash
grep -A2 "polaris.persistence" /tmp/polaris-rendered.yaml | head -20
```

Expected: lines reference `polaris.persistence.type=relational-jdbc` and the Secret-driven JDBC URL/user/password configuration appears (the exact rendering depends on the chart — the goal is to confirm `in-memory` is no longer present).

```bash
grep -c "in-memory" /tmp/polaris-rendered.yaml
```

Expected: `0`.

- [ ] **Step 4: Commit**

```bash
git add 21-polaris/values.yaml
git commit -m "feat(polaris): switch persistence to relational-jdbc"
```

---

### Task 6: Update `21-polaris/README.md`

**Files:**
- Modify: `21-polaris/README.md`

- [ ] **Step 1: Update the `Configuration Notes` table**

Find this row in the `Configuration Notes` table:

```markdown
| `persistence.type` | `in-memory` loses catalog state on pod restart; switch to `relational-jdbc` with PostgreSQL for durability | `in-memory` |
```

Replace with:

```markdown
| `persistence.type` | Backed by PostgreSQL deployed in wave 20 by [`20-polaris-db/`](../20-polaris-db/README.md). Catalog state is durable across pod restarts. | `relational-jdbc` |
```

- [ ] **Step 2: Update the `Sync Wave` section**

Find this paragraph:

```markdown
Wave 21 — depends on MinIO (wave 20). Deploys in parallel with the Debezium CDC connector. The Iceberg Kafka connector (wave 22) and Trino (wave 23) depend on Polaris being ready.
```

Replace with:

```markdown
Wave 21 — depends on MinIO (wave 20, S3 storage) and polaris-db (wave 20, catalog persistence). Deploys in parallel with the Debezium CDC connector. The Iceberg Kafka connector (wave 22) and Trino (wave 23) depend on Polaris being ready.
```

- [ ] **Step 3: Add catalog persistence smoke test to `Post-Install Bootstrap`**

Append the following at the end of the existing `Post-Install Bootstrap` section:

````markdown
### Smoke Test: Catalog Persistence

Verify that catalog state survives a Polaris pod restart (impossible under the old `in-memory` mode):

```bash
# 1. Get the root credentials from the first-start logs
kubectl logs -l app.kubernetes.io/name=polaris -n polaris --context mini \
  | grep -i "root credentials"

# 2. Use the Polaris admin REST API (via kubectl exec) to create a catalog.
#    See the example POST body above in this section.

# 3. Restart Polaris
kubectl rollout restart deployment/polaris -n polaris --context mini
kubectl rollout status deployment/polaris -n polaris --context mini

# 4. List catalogs again — the test catalog must still be present.
#    Use the same admin REST API endpoint.

# 5. Verify the metadata tables exist in PostgreSQL
POD=$(kubectl get pod -l app=polaris-db -n polaris --context mini \
  -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n polaris "$POD" --context mini \
  -- psql -U polaris -d polaris -c '\dt'
```
````

- [ ] **Step 4: Commit**

```bash
git add 21-polaris/README.md
git commit -m "docs(polaris): document polaris-db dependency and persistence smoke test"
```

---

### Task 7: End-to-end validation in the live cluster

This task is manual — it exercises the full deploy + restart cycle to confirm catalog state actually persists. Run only after Tasks 1-6 are committed.

**Files:** none (no code changes)

- [ ] **Step 1: Clean any prior Polaris install (start from a known state)**

```bash
bash 21-polaris/uninstall.sh || true
bash 20-polaris-db/uninstall.sh || true
kubectl delete pvc polaris-db -n polaris --context mini --ignore-not-found
```

- [ ] **Step 2: Deploy `20-polaris-db/` and validate**

```bash
bash 20-polaris-db/install.sh
bash 20-polaris-db/validate.sh
```

Expected: `==> PostgreSQL is ready.`

- [ ] **Step 3: Deploy `21-polaris/` and validate**

```bash
bash 21-polaris/install.sh
bash 21-polaris/validate.sh
```

Expected: `==> Polaris is ready.`

- [ ] **Step 4: Confirm Polaris bootstrapped its schema**

```bash
POD=$(kubectl get pod -l app=polaris-db -n polaris --context mini \
  -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n polaris "$POD" --context mini \
  -- psql -U polaris -d polaris -c '\dt'
```

Expected: a non-empty list of tables (Polaris-managed metadata tables; exact set depends on the 1.3.0 schema).

- [ ] **Step 5: Create a test catalog via the Polaris REST API**

Get root credentials from logs:

```bash
kubectl logs -l app.kubernetes.io/name=polaris -n polaris --context mini \
  | grep -i "root credentials"
```

The output contains `client_id` and `client_secret`. Use them to obtain an OAuth2 token and create a catalog (full request bodies are in `21-polaris/README.md`'s `Post-Install Bootstrap` section).

Record the catalog name you created (e.g. `smoke-test`).

- [ ] **Step 6: Restart Polaris and confirm the catalog survives**

```bash
kubectl rollout restart deployment/polaris -n polaris --context mini
kubectl rollout status deployment/polaris -n polaris --context mini --timeout=300s
```

Then list catalogs via the REST API. Expected: the `smoke-test` catalog from Step 5 is still present.

If it is missing, persistence is broken — investigate whether the Polaris pod is actually pointing at `polaris-db` (check pod env, ConfigMap rendering, and `kubectl logs` for JDBC connection errors).

- [ ] **Step 7: Capture validation evidence (optional but recommended)**

Save the rollout log and catalog list to a scratch file for the PR description:

```bash
{
  echo "## polaris-db end-to-end validation"
  echo
  echo "### Tables in PostgreSQL after Polaris bootstrap"
  kubectl exec -n polaris "$POD" --context mini \
    -- psql -U polaris -d polaris -c '\dt'
  echo
  echo "### Polaris pod restart"
  kubectl rollout history deployment/polaris -n polaris --context mini
} > /tmp/polaris-db-validation.txt
```

No commit for this task — it's verification only.

---

## Self-Review

**1. Spec coverage:**
- Spec §`Component: 20-polaris-db/` — Task 1 (manifests), Task 2 (scripts), Task 3 (README). ✓
- Spec §`Changes to 21-polaris/` — Task 5 (values.yaml), Task 6 (README). ✓
- Spec §`ArgoCD App Template` — Task 4. ✓
- Spec §`Verification` end-to-end smoke test — Task 7. ✓
- Spec §`Risks and Trade-offs` — encoded in Task 1 deployment YAML comment (probe duplication) and Task 2/3 uninstall behaviour (PVC retention).

**2. Placeholder scan:** No "TBD", "TODO", "implement later", or vague handwaving. All YAML/bash/markdown content is shown in full.

**3. Type/name consistency check:**
- Secret name `polaris-db` consistent across Tasks 1, 2, 5, 6.
- Secret keys `username`/`password`/`database`/`jdbcUrl` consistent in Task 1 (Secret) → Task 1 (Deployment `secretKeyRef`) → Task 5 (Polaris values).
- Probe args `pg_isready -U polaris -d polaris` match the Secret's `username` and `database` values.
- Service DNS `polaris-db.polaris.svc.cluster.local:5432` consistent with the Service definition (port 5432) and Secret's `jdbcUrl`.
- ArgoCD app `path: 20-polaris-db` matches the new directory name.
- Sync-wave `"20"` consistent across the ArgoCD app annotation and README sync-wave section.
