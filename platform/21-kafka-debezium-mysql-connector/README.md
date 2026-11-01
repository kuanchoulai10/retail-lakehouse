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

The KafkaConnect has a memory limit of `1Gi` and a request of `640Mi` (it used 408 MiB after a 30 minute soak) with heap `-Xms128m -Xmx512m` and `MaxMetaspaceSize=256m`. The pod used about 454 MiB before the limit and about 500 MiB after. The request is sized from usage, not set equal to the limit: with request = limit on Kafka, both KafkaConnects, RustFS and Jaeger the node had 27013Mi of 28005Mi allocatable requested, and Spark maintenance executors (1433Mi each) could not be scheduled.
