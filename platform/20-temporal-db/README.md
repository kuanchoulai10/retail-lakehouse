# Temporal PostgreSQL

Deploys PostgreSQL 17.11 as the persistent store for the Temporal server (default and visibility stores), into the `temporal` namespace. This wave also creates the `temporal` namespace. The Temporal databases (`temporal`, `temporal_visibility`) and their schemas are created by the chart's schema job in `21-temporal`.

## Deployed Resources

```
Namespace: temporal
├── temporal-db                           (Deployment, strategy Recreate)
├── temporal-db                           (Service, port 5432)
├── temporal-db                           (PersistentVolumeClaim, 5Gi)
└── temporal-db                           (Secret: username/password/database)
```

## Pods

| Pod | Purpose |
|-----|---------|
| `temporal-db` | PostgreSQL 17.11 storing Temporal workflow state and visibility data |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `temporal-db.temporal.svc.cluster.local` | 5432 | PostgreSQL connection endpoint |

## Sync Wave

Wave 20 — deploys in parallel with the other wave-20 components. Temporal (wave 21) depends on it.

## Connection Info

The Secret `temporal-db` in namespace `temporal` holds `username`, `password` and `database` (all `temporal`, dev-only plaintext). The Deployment reads them via `secretKeyRef`; the Temporal chart reads `password` via `existingSecret`.

## Installation

```bash
KUBE_CONTEXT=retail-lakehouse bash platform/20-temporal-db/bootstrap.sh
```

## Validation

```bash
KUBE_CONTEXT=retail-lakehouse bash platform/20-temporal-db/validate.sh
```
