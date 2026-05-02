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
