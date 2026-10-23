# MySQL

Deploys a MySQL instance in the `ecommerce-app` namespace using the Debezium example MySQL image, which ships with binlog-based CDC pre-enabled. This database serves as the source system for the CDC pipeline and contains the `inventory` database used by the Debezium connector.

## Deployed Resources

```
Namespace: ecommerce-app
└── mysql                                (Deployment)
```

## Namespaces

- `ecommerce-app` (created by this wave's `bootstrap.sh`)

## Pods

| Pod | Purpose |
|-----|---------|
| `mysql` | MySQL source database with binlog CDC enabled |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `mysql` | 3306 | MySQL database (headless) |
