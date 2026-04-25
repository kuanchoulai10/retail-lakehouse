# Table Maintenance: PostgreSQL Deployment Design

## Context

The table-maintenance backend and scheduler currently share a SQLite file on a hostPath volume. This is fragile — no concurrent write safety, no persistence guarantees, and no isolation between components. We need a proper PostgreSQL database that both services connect to, deployed as three independent components following the repo's established pattern.

## Decision: No Migration Tool Yet

Schema is created at runtime via `metadata.create_all(engine)` (SQLAlchemy). This is idempotent and sufficient while the schema is still evolving. Alembic will be introduced later when the schema stabilizes.

## Deployment Topology

```
25-tbl-maint-db/        PostgreSQL 17 (Deployment + PVC + Service)
       ↓
25-tbl-maint-bcknd/     FastAPI Backend (Deployment + Service + RBAC)
       ↓
25-tbl-maint-schdlr/    Scheduler (Deployment)
```

Each component has its own `install.sh` and `validate.sh`. Ordering is enforced by `taskfile.yml`.

## Component Details

### 25-tbl-maint-db

**Purpose:** Single-replica PostgreSQL for dev/demo.

**K8s Resources:**
- `postgres-pvc.yaml` — 1Gi PersistentVolumeClaim (default StorageClass)
- `postgres-deployment.yaml` — postgres:17-alpine, mounts PVC at `/var/lib/postgresql/data`, env: `POSTGRES_DB=table_maintenance`, `POSTGRES_USER=tm`, `POSTGRES_PASSWORD=tm`
- `postgres-service.yaml` — ClusterIP `tbl-maint-db`, port 5432

**Connection string:** `postgresql+psycopg://tm:tm@tbl-maint-db.default.svc:5432/table_maintenance`

**install.sh:** `kubectl apply` all three manifests.
**validate.sh:** `kubectl wait pod --for=condition=Ready` + exec `pg_isready` to confirm PostgreSQL is accepting connections.

### 25-tbl-maint-bcknd

**Purpose:** FastAPI backend serving the table-maintenance API.

**K8s Resources:**
- `backend-deployment.yaml` — existing image, env updated to point at PostgreSQL
- `backend-service.yaml` — ClusterIP, port 8000
- `backend-rbac.yaml` — ServiceAccount + RBAC for SparkApplication management

**Env changes from current `25-table-maintenance/`:**
- Add: `BACKEND_DATABASE_BACKEND=postgres`
- Add: `BACKEND_POSTGRES__DB_URL=postgresql+psycopg://tm:tm@tbl-maint-db.default.svc:5432/table_maintenance`
- Add: `BACKEND_JOBS_REPO_ADAPTER=sql`
- Add: `BACKEND_JOB_RUNS_REPO_ADAPTER=sql`
- Remove: `BACKEND_SQLITE__DB_PATH`, hostPath volume

Tables are created automatically on startup via `metadata.create_all(engine)` in the FastAPI lifespan hook.

**install.sh:** `kubectl apply` manifests + `kubectl rollout status`.
**validate.sh:** `kubectl rollout status` + port-forward + `curl /health`.

### 25-tbl-maint-schdlr

**Purpose:** Standalone scheduler polling DB for due jobs.

**K8s Resources:**
- `scheduler-deployment.yaml` — existing image, env updated to point at PostgreSQL

**Env changes:**
- `SCHEDULER_DATABASE_URL=postgresql+psycopg://tm:tm@tbl-maint-db.default.svc:5432/table_maintenance`
- Remove: hostPath volume

**install.sh:** `kubectl apply` + `kubectl rollout status`.
**validate.sh:** `kubectl rollout status` + verify logs contain `Scheduler tick`.

## taskfile.yml Integration

```yaml
- bash 25-tbl-maint-db/install.sh
- bash 25-tbl-maint-db/validate.sh
- bash 25-tbl-maint-bcknd/install.sh
- bash 25-tbl-maint-bcknd/validate.sh
- bash 25-tbl-maint-schdlr/install.sh
- bash 25-tbl-maint-schdlr/validate.sh
```

## Old `25-table-maintenance/` Directory

Retained for SparkApplication-related files (`sparkapplication-rewrite-data-files.yaml`, `build.sh`). Backend/scheduler manifests are moved to the new directories.

## Verification

After all three components are deployed:
1. All pods Running: `kubectl get pods -l app in (tbl-maint-db, table-maintenance-backend, table-maintenance-scheduler)`
2. Backend healthy: `curl /health` via port-forward
3. End-to-end: POST a Job with `cron` + `enabled=true` → scheduler creates JobRun(PENDING) within one tick interval
