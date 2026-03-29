# MySQL

Deploys a MySQL instance in the `kafka-cdc` namespace using the Debezium example MySQL image, which ships with binlog-based CDC pre-enabled. This database serves as the source system for the CDC pipeline and contains the `inventory` database used by the Debezium connector.

## Deployed Resources

```
Namespace: kafka-cdc
└── mysql                                (Deployment)
```

## Namespaces

- `kafka-cdc` (pre-existing, created by `20-kafka-cluster`)

## Pods

| Pod | Purpose |
|-----|---------|
| `mysql` | MySQL source database with binlog CDC enabled |
