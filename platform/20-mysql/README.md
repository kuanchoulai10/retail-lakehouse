# MySQL

Deploys a MySQL instance in the `ecommerce-app` namespace using the Debezium example MySQL image, which ships with binlog-based CDC pre-enabled. This database serves as the source system for the CDC pipeline and contains the `inventory` database used by the Debezium connector.

## Deployed Resources

```
Namespace: ecommerce-app
├── mysql                                (Deployment)
└── mysql                                (PersistentVolumeClaim, 5Gi, mounted at /var/lib/mysql)
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

## Storage

The data directory `/var/lib/mysql` is on the PersistentVolumeClaim `mysql` (5Gi, default StorageClass), so the `inventory` data and the binlog survive a pod restart and Debezium's stored binlog position stays valid. The image seeds `inventory` only when the data directory is empty, that is on the first start of a new claim. The claim is removed with the cluster (`task offboard`); deleting it alone resets the database and needs a new Debezium snapshot.
