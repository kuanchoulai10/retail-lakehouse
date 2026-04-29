# Polaris PostgreSQL Backing Store Design

## Context

Apache Polaris is currently deployed by `21-polaris/` with `persistence.type: in-memory`. Catalog state (namespaces, tables, schemas, principals) is lost on every pod restart, making the deployment unfit for any persistent workload. The official Polaris Helm chart does not bundle a database — it expects an external PostgreSQL referenced through a Kubernetes Secret containing `username`, `password`, and `jdbcUrl` keys.

This spec defines a new sibling component `20-polaris-db/` that deploys PostgreSQL into the existing `polaris` namespace, plus the changes to `21-polaris/` and the ArgoCD app-of-apps to wire them together.

## Goals

- Provide a durable PostgreSQL backing store for Polaris catalog metadata.
- Keep the new component aligned with the repo's existing infrastructure conventions (sync-wave folder naming, install/uninstall/validate scripts, ArgoCD app templates).
- Enable end-to-end verification that catalog state survives a Polaris pod restart.

## Non-Goals

- Production-grade PostgreSQL (HA, backups, PITR). A future migration to CloudNativePG or Bitnami Operator is out of scope.
- StatefulSet semantics (stable network identity, automatic PVC lifecycle). Deployment + standalone PVC is sufficient for the current single-replica dev/demo target.
- SOPS-encrypted credentials. Hardcoded plain manifests follow the precedent set by `25-tbl-maint-db/`.
- ServiceMonitor / postgres-exporter sidecar. Database observability is deferred.

## Deployment Topology

```
wave 20: 20-minio  ─┐
        20-polaris-db (new) ─┐
                              ├── shared namespace `polaris`
wave 21: 21-polaris ──────────┘   (consumes polaris-db Secret)
wave 22: 22-kafka-iceberg-connector
wave 23: 23-trino
```

Both `20-polaris-db` and `21-polaris` deploy into namespace `polaris`. The DB is provisioned in wave 20 so its Service and Secret exist before Polaris starts in wave 21.

## Component: `20-polaris-db/`

### Files

```
20-polaris-db/
├── README.md
├── polaris-db-secret.yaml       # Single source of truth for credentials + JDBC URL
├── polaris-db-pvc.yaml          # 5Gi PersistentVolumeClaim
├── polaris-db-deployment.yaml   # postgres:17-alpine, reads creds via secretKeyRef
├── polaris-db-service.yaml      # ClusterIP, port 5432
├── install.sh                   # Apply manifests in order
├── uninstall.sh                 # Reverse delete; PVC intentionally retained
└── validate.sh                  # Wait pod ready + pg_isready
```

### Credentials (single shared Secret)

Both the PostgreSQL Deployment and the Polaris Helm chart read from the same `polaris-db` Secret in namespace `polaris`. This eliminates duplicate credential definitions and provides a single change-point for rotation.

| Key | Value | Consumer |
|-----|-------|----------|
| `username` | `polaris` | postgres `POSTGRES_USER`, Polaris JDBC user |
| `password` | `polaris` | postgres `POSTGRES_PASSWORD`, Polaris JDBC password |
| `database` | `polaris` | postgres `POSTGRES_DB` |
| `jdbcUrl` | `jdbc:postgresql://polaris-db.polaris.svc.cluster.local:5432/polaris` | Polaris JDBC connection URL |

The deployment uses `valueFrom.secretKeyRef` rather than hardcoded env values, so changing the password only requires editing the Secret.

### Deployment

- Image: `postgres:17-alpine` (matches `25-tbl-maint-db`).
- Replicas: 1.
- `PGDATA=/var/lib/postgresql/data/pgdata` to keep the data directory under the PVC mount.
- Liveness and readiness probes both use `pg_isready -U polaris -d polaris`. These username/database values are duplicated from the Secret because probes cannot read Secrets — if the Secret values change, the probe args must be updated in lockstep.
- No resource requests/limits (matches `25-tbl-maint-db`; minikube dev environment).

### PVC

5Gi RWO claim, default StorageClass. Larger than `25-tbl-maint-db`'s 1Gi to accommodate catalog growth across multiple realms/principals.

### Service

ClusterIP `polaris-db.polaris.svc.cluster.local`, port 5432, named port `postgres`.

### install.sh

Creates the namespace (idempotent via `--dry-run=client | apply`) then applies Secret, PVC, Deployment, Service in order. Ordering matters because the Deployment references the Secret via `secretKeyRef`.

### uninstall.sh

Deletes Service, Deployment, Secret. **PVC is intentionally not deleted** to prevent accidental data loss; an explicit warning is printed instructing the operator to run `kubectl delete pvc polaris-db -n polaris` if they want to wipe data.

### validate.sh

`kubectl wait pod -l app=polaris-db --for=condition=Ready` then `kubectl exec ... -- pg_isready -U polaris -d polaris` to confirm the database is accepting connections.

## Changes to `21-polaris/`

### `values.yaml`

Switch persistence from `in-memory` to `relational-jdbc` and reference the shared Secret:

```yaml
persistence:
  type: relational-jdbc
  relationalJdbc:
    secret:
      name: polaris-db
      username: username
      password: password
      jdbcUrl: jdbcUrl
```

The Polaris 1.3.0 image ships with a PostgreSQL JDBC driver, so no extra init container or volume mount is needed. On first start Polaris auto-creates its schema in the target database.

### `README.md`

Two updates:

1. In the **Configuration Notes** table, replace the `persistence.type` row's "switch to relational-jdbc with PostgreSQL for durability" note with: "Persistence is backed by PostgreSQL deployed in wave 20 by `20-polaris-db/`. Catalog state is durable across pod restarts."
2. In the **Sync Wave** section, change "Wave 21 — depends on MinIO (wave 20)" to "Wave 21 — depends on MinIO (wave 20, S3 storage) and polaris-db (wave 20, catalog persistence)."

The existing **Post-Install Bootstrap** section is augmented with a smoke test to verify catalog persistence (see Verification below).

## ArgoCD App Template

Add `charts/app-of-apps/templates/20-polaris-db.yaml`, mirroring the structure of `20-minio.yaml`:

```yaml
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

## Verification

End-to-end smoke test (run after both `20-polaris-db/` and `21-polaris/` are deployed and validated):

1. `bash 20-polaris-db/install.sh && bash 20-polaris-db/validate.sh` — PG ready.
2. `bash 21-polaris/install.sh && bash 21-polaris/validate.sh` — Polaris pod ready.
3. **Catalog persistence test:**
   - Retrieve root credentials: `kubectl logs -l app.kubernetes.io/name=polaris -n polaris | grep "root credentials"`.
   - Use the Polaris REST API (via `kubectl exec`) to create a test catalog.
   - `kubectl rollout restart deployment/polaris -n polaris`.
   - Wait for pod ready, list catalogs again — the test catalog must still be present.
4. **Schema check:** `kubectl exec polaris-db-<pod> -n polaris -- psql -U polaris -d polaris -c '\dt'` should list the metadata tables Polaris bootstrapped.

## Risks and Trade-offs

- **Hardcoded credentials in plain manifests.** Anyone with repo read access can see the password. Acceptable for a dev/demo cluster; if this design is reused in a shared environment, switch to SOPS-encrypted Secrets following the `21-polaris/polaris-storage-secret.yaml` pattern.
- **Probe args duplicate Secret values.** `pg_isready -U polaris -d polaris` is hardcoded in the Deployment because probes cannot read Secrets. A username/password/database change requires editing both the Secret and the Deployment probe args. Documented in the Deployment YAML comments.
- **Single replica, no backups.** Pod eviction or PVC corruption loses all catalog state. Acceptable trade-off given the non-goal scope; the `uninstall.sh` PVC-retention behaviour partially mitigates accidental loss.
- **Sync-wave coupling.** If ArgoCD applies wave 20 components in parallel and Polaris (wave 21) starts before polaris-db is fully ready, Polaris will crashloop briefly. The Polaris pod's restart policy handles this; once polaris-db is Ready, the next Polaris restart succeeds.
