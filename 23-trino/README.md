# Trino

Deploys Trino, a distributed SQL query engine, via Helm into the `trino` namespace. Trino federates queries across the Iceberg lakehouse on MinIO and BigQuery. The installation generates TLS certificates and a BigQuery service account secret before running the Helm chart.

## Deployed Resources

```
Namespace: trino
├── trino-coordinator                    (Deployment)
└── trino-worker                         (Deployment)
```

## Namespaces

- `trino`

## Pods

| Pod | Purpose |
|-----|---------|
| `trino-coordinator` | Parses queries, builds execution plans, and coordinates workers |
| `trino-worker` | Executes query fragments and reads data from sources |
