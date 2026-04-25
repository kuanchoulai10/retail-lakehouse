# Table Maintenance PostgreSQL Deployment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy PostgreSQL as a shared database for the table-maintenance backend and scheduler, split into three independently deployable components with install/validate scripts.

**Architecture:** Three new directories (`25-tbl-maint-db`, `25-tbl-maint-bcknd`, `25-tbl-maint-schdlr`) each with K8s manifests + install.sh + validate.sh. The old `25-table-maintenance/` is cleaned up to only keep SparkApplication files. Backend creates tables on startup via `metadata.create_all()` — no migration tool.

**Tech Stack:** PostgreSQL 17, Kubernetes Deployments, PVC, kubectl, bash scripts

**Spec:** `docs/superpowers/specs/2026-04-24-tbl-maint-postgresql-deploy-design.md`

---

## File Map

```
25-tbl-maint-db/                      (NEW directory)
├── postgres-pvc.yaml
├── postgres-deployment.yaml
├── postgres-service.yaml
├── install.sh
└── validate.sh

25-tbl-maint-bcknd/                   (NEW directory)
├── backend-deployment.yaml           (moved from 25-table-maintenance/, env updated)
├── backend-service.yaml              (extracted from backend-deployment.yaml)
├── backend-rbac.yaml                 (moved from 25-table-maintenance/)
├── install.sh
└── validate.sh

25-tbl-maint-schdlr/                  (NEW directory)
├── scheduler-deployment.yaml         (moved from 25-table-maintenance/, env updated)
├── install.sh
└── validate.sh

25-table-maintenance/                 (CLEANED UP — remove moved files)
├── build.sh                          (keep)
├── sparkapplication-rewrite-data-files.yaml  (keep)
├── install.sh                        (keep — submits SparkApp)
└── validate.sh                       (keep — checks SparkApp)

taskfile.yml                          (MODIFY — add new entries to bootstrap + validate)
.claude/skills/minikube-deploy/SKILL.md  (MODIFY — update manifest paths)
```

---

### Task 1: Create `25-tbl-maint-db/` — PostgreSQL K8s manifests

**Files:**
- Create: `25-tbl-maint-db/postgres-pvc.yaml`
- Create: `25-tbl-maint-db/postgres-deployment.yaml`
- Create: `25-tbl-maint-db/postgres-service.yaml`

- [ ] **Step 1: Create PVC manifest**

```yaml
# 25-tbl-maint-db/postgres-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: tbl-maint-db
  namespace: default
  labels:
    app: tbl-maint-db
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

- [ ] **Step 2: Create Deployment manifest**

```yaml
# 25-tbl-maint-db/postgres-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tbl-maint-db
  namespace: default
  labels:
    app: tbl-maint-db
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tbl-maint-db
  template:
    metadata:
      labels:
        app: tbl-maint-db
    spec:
      containers:
        - name: postgres
          image: postgres:17-alpine
          env:
            - name: POSTGRES_DB
              value: "table_maintenance"
            - name: POSTGRES_USER
              value: "tm"
            - name: POSTGRES_PASSWORD
              value: "tm"
            - name: PGDATA
              value: "/var/lib/postgresql/data/pgdata"
          ports:
            - name: postgres
              containerPort: 5432
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "tm", "-d", "table_maintenance"]
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            exec:
              command: ["pg_isready", "-U", "tm", "-d", "table_maintenance"]
            initialDelaySeconds: 15
            periodSeconds: 10
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: tbl-maint-db
```

- [ ] **Step 3: Create Service manifest**

```yaml
# 25-tbl-maint-db/postgres-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: tbl-maint-db
  namespace: default
  labels:
    app: tbl-maint-db
spec:
  selector:
    app: tbl-maint-db
  ports:
    - name: postgres
      port: 5432
      targetPort: postgres
```

- [ ] **Step 4: Commit**

```bash
git add 25-tbl-maint-db/
git commit -m "chore(deploy): add PostgreSQL K8s manifests for table-maintenance"
```

---

### Task 2: Create `25-tbl-maint-db/` — install.sh and validate.sh

**Files:**
- Create: `25-tbl-maint-db/install.sh`
- Create: `25-tbl-maint-db/validate.sh`

- [ ] **Step 1: Create install.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying PostgreSQL for table-maintenance (context: ${KUBE_CONTEXT})"

kubectl apply -f "$SCRIPT_DIR/postgres-pvc.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/postgres-deployment.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/postgres-service.yaml" --context "${KUBE_CONTEXT}"

echo "==> Done."
```

- [ ] **Step 2: Create validate.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating PostgreSQL for table-maintenance (context: ${KUBE_CONTEXT})"

kubectl wait pod \
  -l app=tbl-maint-db \
  -n default \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

echo "==> Verifying PostgreSQL is accepting connections..."
kubectl exec -n default \
  "$(kubectl get pod -l app=tbl-maint-db -n default --context "${KUBE_CONTEXT}" -o jsonpath='{.items[0].metadata.name}')" \
  --context "${KUBE_CONTEXT}" \
  -- pg_isready -U tm -d table_maintenance

echo "==> PostgreSQL is ready."
```

- [ ] **Step 3: Make scripts executable**

```bash
chmod +x 25-tbl-maint-db/install.sh 25-tbl-maint-db/validate.sh
```

- [ ] **Step 4: Commit**

```bash
git add 25-tbl-maint-db/
git commit -m "chore(deploy): add install/validate scripts for table-maintenance PostgreSQL"
```

---

### Task 3: Create `25-tbl-maint-bcknd/` — Backend manifests and scripts

**Files:**
- Create: `25-tbl-maint-bcknd/backend-deployment.yaml`
- Create: `25-tbl-maint-bcknd/backend-service.yaml`
- Create: `25-tbl-maint-bcknd/backend-rbac.yaml`
- Create: `25-tbl-maint-bcknd/install.sh`
- Create: `25-tbl-maint-bcknd/validate.sh`

- [ ] **Step 1: Create backend-deployment.yaml**

Based on the existing `25-table-maintenance/backend-deployment.yaml` but with PostgreSQL env vars, no SQLite, no hostPath volume. The Deployment and Service are separated into individual files.

```yaml
# 25-tbl-maint-bcknd/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: table-maintenance-backend
  namespace: default
  labels:
    app: table-maintenance-backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: table-maintenance-backend
  template:
    metadata:
      labels:
        app: table-maintenance-backend
    spec:
      serviceAccountName: table-maintenance-backend
      containers:
        - name: backend
          image: localhost:5001/table-maintenance-backend:20260422-014020
          imagePullPolicy: Never
          env:
            - name: BACKEND_DATABASE_BACKEND
              value: "postgres"
            - name: BACKEND_POSTGRES__DB_URL
              value: "postgresql+psycopg://tm:tm@tbl-maint-db.default.svc:5432/table_maintenance"
            - name: BACKEND_JOBS_REPO_ADAPTER
              value: "sql"
            - name: BACKEND_JOB_RUNS_REPO_ADAPTER
              value: "sql"
            - name: BACKEND_ICEBERG_CATALOG_URI
              value: "http://polaris.polaris.svc.cluster.local:8181/api/catalog"
            - name: BACKEND_ICEBERG_CATALOG_CREDENTIAL
              value: "root:secret"
            - name: BACKEND_ICEBERG_CATALOG_WAREHOUSE
              value: "iceberg"
            - name: BACKEND_ICEBERG_CATALOG_SCOPE
              value: "PRINCIPAL_ROLE:ALL"
          ports:
            - name: http
              containerPort: 8000
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 3
            periodSeconds: 5
```

- [ ] **Step 2: Create backend-service.yaml**

```yaml
# 25-tbl-maint-bcknd/backend-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: table-maintenance-backend
  namespace: default
  labels:
    app: table-maintenance-backend
spec:
  selector:
    app: table-maintenance-backend
  ports:
    - name: http
      port: 8000
      targetPort: http
```

- [ ] **Step 3: Create backend-rbac.yaml**

Copy from existing `25-table-maintenance/backend-rbac.yaml` (unchanged):

```yaml
# 25-tbl-maint-bcknd/backend-rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: table-maintenance-backend
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: table-maintenance-backend
  namespace: default
rules:
  - apiGroups: ["sparkoperator.k8s.io"]
    resources: ["sparkapplications", "scheduledsparkapplications"]
    verbs: ["get", "list", "create", "delete", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: table-maintenance-backend
  namespace: default
subjects:
  - kind: ServiceAccount
    name: table-maintenance-backend
    namespace: default
roleRef:
  kind: Role
  name: table-maintenance-backend
  apiGroup: rbac.authorization.k8s.io
```

- [ ] **Step 4: Create install.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying table-maintenance backend (context: ${KUBE_CONTEXT})"

kubectl apply -f "$SCRIPT_DIR/backend-rbac.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/backend-service.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/backend-deployment.yaml" --context "${KUBE_CONTEXT}"

echo "==> Waiting for rollout..."
kubectl rollout status deployment/table-maintenance-backend \
  -n default --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Done."
```

- [ ] **Step 5: Create validate.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating table-maintenance backend (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/table-maintenance-backend \
  -n default --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Checking health endpoint..."
kubectl exec -n default \
  "$(kubectl get pod -l app=table-maintenance-backend -n default --context "${KUBE_CONTEXT}" -o jsonpath='{.items[0].metadata.name}')" \
  --context "${KUBE_CONTEXT}" \
  -- python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"

echo "==> Backend is ready."
```

- [ ] **Step 6: Make scripts executable and commit**

```bash
chmod +x 25-tbl-maint-bcknd/install.sh 25-tbl-maint-bcknd/validate.sh
git add 25-tbl-maint-bcknd/
git commit -m "chore(deploy): add backend K8s manifests and install/validate scripts"
```

---

### Task 4: Create `25-tbl-maint-schdlr/` — Scheduler manifests and scripts

**Files:**
- Create: `25-tbl-maint-schdlr/scheduler-deployment.yaml`
- Create: `25-tbl-maint-schdlr/install.sh`
- Create: `25-tbl-maint-schdlr/validate.sh`

- [ ] **Step 1: Create scheduler-deployment.yaml**

```yaml
# 25-tbl-maint-schdlr/scheduler-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: table-maintenance-scheduler
  namespace: default
  labels:
    app: table-maintenance-scheduler
spec:
  replicas: 1
  selector:
    matchLabels:
      app: table-maintenance-scheduler
  template:
    metadata:
      labels:
        app: table-maintenance-scheduler
    spec:
      containers:
        - name: scheduler
          image: localhost:5001/table-maintenance-scheduler:20260422-230712
          imagePullPolicy: Never
          env:
            - name: SCHEDULER_DATABASE_URL
              value: "postgresql+psycopg://tm:tm@tbl-maint-db.default.svc:5432/table_maintenance"
            - name: SCHEDULER_INTERVAL_SECONDS
              value: "30"
```

- [ ] **Step 2: Create install.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying table-maintenance scheduler (context: ${KUBE_CONTEXT})"

kubectl apply -f "$SCRIPT_DIR/scheduler-deployment.yaml" --context "${KUBE_CONTEXT}"

echo "==> Waiting for rollout..."
kubectl rollout status deployment/table-maintenance-scheduler \
  -n default --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Done."
```

- [ ] **Step 3: Create validate.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating table-maintenance scheduler (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/table-maintenance-scheduler \
  -n default --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Checking scheduler logs for tick output..."
POD=$(kubectl get pod -l app=table-maintenance-scheduler -n default \
  --context "${KUBE_CONTEXT}" -o jsonpath='{.items[0].metadata.name}')
kubectl logs "$POD" -n default --context "${KUBE_CONTEXT}" --tail=5 | grep -q "Scheduler tick"

echo "==> Scheduler is ready."
```

- [ ] **Step 4: Make scripts executable and commit**

```bash
chmod +x 25-tbl-maint-schdlr/install.sh 25-tbl-maint-schdlr/validate.sh
git add 25-tbl-maint-schdlr/
git commit -m "chore(deploy): add scheduler K8s manifests and install/validate scripts"
```

---

### Task 5: Clean up `25-table-maintenance/` and remove old manifests

**Files:**
- Delete: `25-table-maintenance/backend-deployment.yaml`
- Delete: `25-table-maintenance/backend-rbac.yaml`
- Delete: `25-table-maintenance/scheduler-deployment.yaml`

- [ ] **Step 1: Delete moved manifests**

```bash
git rm 25-table-maintenance/backend-deployment.yaml
git rm 25-table-maintenance/backend-rbac.yaml
git rm 25-table-maintenance/scheduler-deployment.yaml
```

- [ ] **Step 2: Verify remaining files are SparkApp-only**

```bash
ls 25-table-maintenance/
```

Expected: `build.sh`, `install.sh`, `sparkapplication-rewrite-data-files.yaml`, `validate.sh`

- [ ] **Step 3: Commit**

```bash
git commit -m "chore(deploy): remove moved backend/scheduler manifests from 25-table-maintenance"
```

---

### Task 6: Update `taskfile.yml` with new deployment entries

**Files:**
- Modify: `taskfile.yml`

- [ ] **Step 1: Add entries to `bootstrap-apps-by-scripts`**

Insert after the `30-thanos` lines (at the end of the bootstrap sequence):

```yaml
      - bash 25-tbl-maint-db/install.sh
      - bash 25-tbl-maint-db/validate.sh
      - bash 25-tbl-maint-bcknd/install.sh
      - bash 25-tbl-maint-bcknd/validate.sh
      - bash 25-tbl-maint-schdlr/install.sh
      - bash 25-tbl-maint-schdlr/validate.sh
```

- [ ] **Step 2: Add validate task entries**

Add three new internal tasks inside the `# --8<-- [start:validate]` section, before `# --8<-- [end:validate]`:

```yaml
  validate-tbl-maint-db:
    internal: true
    env:
      KUBE_CONTEXT: '{{.KUBE_CONTEXT}}'
    cmds:
      - bash 25-tbl-maint-db/validate.sh

  validate-tbl-maint-bcknd:
    internal: true
    env:
      KUBE_CONTEXT: '{{.KUBE_CONTEXT}}'
    cmds:
      - bash 25-tbl-maint-bcknd/validate.sh

  validate-tbl-maint-schdlr:
    internal: true
    env:
      KUBE_CONTEXT: '{{.KUBE_CONTEXT}}'
    cmds:
      - bash 25-tbl-maint-schdlr/validate.sh
```

- [ ] **Step 3: Add to `validate-apps` deps**

Add inside the `validate-apps` task's `deps` list:

```yaml
      - task: validate-tbl-maint-db
        vars:
          KUBE_CONTEXT: "{{.KUBE_CONTEXT}}"
      - task: validate-tbl-maint-bcknd
        vars:
          KUBE_CONTEXT: "{{.KUBE_CONTEXT}}"
      - task: validate-tbl-maint-schdlr
        vars:
          KUBE_CONTEXT: "{{.KUBE_CONTEXT}}"
```

- [ ] **Step 4: Commit**

```bash
git add taskfile.yml
git commit -m "chore(deploy): add table-maintenance components to bootstrap and validate tasks"
```

---

### Task 7: Update minikube-deploy skill manifest paths

**Files:**
- Modify: `.claude/skills/minikube-deploy/SKILL.md`

- [ ] **Step 1: Update Known Images table**

Change the Deploy Manifest column for backend and scheduler:

| Image Name | Dockerfile | Build Context | Deploy Manifest | Deploy Kind |
|-----------|-----------|--------------|----------------|------------|
| `table-maintenance-spark` | `src/table-maintenance/runtime/spark/Dockerfile` | `src/table-maintenance/runtime/spark/` | `25-table-maintenance/sparkapplication-rewrite-data-files.yaml` | SparkApplication |
| `table-maintenance-backend` | `src/table-maintenance/backend/Dockerfile` | `src/table-maintenance/backend/` | `25-tbl-maint-bcknd/backend-deployment.yaml` | Deployment + Service |
| `table-maintenance-scheduler` | `src/table-maintenance/scheduler/Dockerfile` | `src/table-maintenance/` | `25-tbl-maint-schdlr/scheduler-deployment.yaml` | Deployment |

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/minikube-deploy/SKILL.md
git commit -m "docs(skill): update minikube-deploy manifest paths for new directory structure"
```

---

### Task 8: Deploy and verify end-to-end

- [ ] **Step 1: Delete old deployments**

```bash
kubectl delete deployment table-maintenance-backend table-maintenance-scheduler -n default --ignore-not-found
```

- [ ] **Step 2: Deploy PostgreSQL**

```bash
bash 25-tbl-maint-db/install.sh
bash 25-tbl-maint-db/validate.sh
```

Expected: `==> PostgreSQL is ready.`

- [ ] **Step 3: Deploy backend**

```bash
bash 25-tbl-maint-bcknd/install.sh
bash 25-tbl-maint-bcknd/validate.sh
```

Expected: `==> Backend is ready.`

- [ ] **Step 4: Deploy scheduler**

```bash
bash 25-tbl-maint-schdlr/install.sh
bash 25-tbl-maint-schdlr/validate.sh
```

Expected: `==> Scheduler is ready.`

- [ ] **Step 5: Verify all pods running**

```bash
kubectl get pods -n default | grep -E 'tbl-maint-db|table-maintenance'
```

Expected: three pods, all `1/1 Running`.

- [ ] **Step 6: End-to-end test — create a job with cron**

```bash
# Port-forward backend
kubectl port-forward svc/table-maintenance-backend 8000:8000 -n default &
PF_PID=$!
sleep 2

# Create an enabled job with cron
curl -s -X POST http://localhost:8000/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "job_type": "expire_snapshots",
    "catalog": "iceberg",
    "expire_snapshots": {"table": "inventory.orders"},
    "cron": "* * * * *",
    "enabled": true
  }' | python3 -m json.tool

# Wait for scheduler to create a JobRun (at most ~30s)
sleep 35

# Check runs were created
JOB_ID=$(curl -s http://localhost:8000/v1/jobs | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
curl -s "http://localhost:8000/v1/jobs/${JOB_ID}/runs" | python3 -m json.tool

# Clean up port-forward
kill $PF_PID
```

Expected: at least one JobRun with `status: "pending"`.
