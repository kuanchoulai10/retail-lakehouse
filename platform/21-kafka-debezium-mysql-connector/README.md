# Debezium MySQL Connector

Deploys a Strimzi KafkaConnect cluster with the Debezium MySQL connector plugin installed. The connector captures row-level changes from the MySQL `inventory` database and publishes them as events to Kafka topics. Strimzi builds a custom connector image and pushes it to the in-cluster registry.

## Deployed Resources

```
Namespace: kafka
├── debezium-connect-cluster-connect-0   (Pod, KafkaConnect)
└── debezium-connector                   (KafkaConnector)
```

## Namespaces

- `kafka` (pre-existing, created by `20-kafka-cluster`)

## Pods

| Pod | Purpose |
|-----|---------|
| `debezium-connect-cluster-connect-0` | Runs the Debezium MySQL connector worker |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `debezium-connect-cluster-connect-api` | 8083 | Kafka Connect REST API |
| `debezium-connect-cluster-connect` | 8083 | Headless service for Connect worker pods |

## Memory

The KafkaConnect has a memory request of `640Mi` and a limit of `1Gi` with heap `-Xms128m -Xmx512m` and `MaxMetaspaceSize=256m`. The request is sized from usage, not set equal to the limit: with request = limit on Kafka, both KafkaConnects, RustFS and Jaeger the node had 27013Mi of 28005Mi allocatable requested, and Spark maintenance executors (1433Mi each) could not be scheduled.

Measured on the deployed configuration (2026-11-01, after a clean onboard, a table maintenance `e2e.sh` run and a 30 minute soak with no changes, 14:05–14:35): 452 MiB, no restart. It used about 454 MiB before the limit.
