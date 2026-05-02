# Debezium MySQL Connector

Deploys a Strimzi KafkaConnect cluster with the Debezium MySQL connector plugin installed. The connector captures row-level changes from the MySQL `inventory` database and publishes them as events to Kafka topics. Strimzi builds a custom connector image and pushes it to the in-cluster registry.

## Deployed Resources

```
Namespace: kafka-cdc
├── debezium-connect-cluster-connect-0   (Pod, KafkaConnect)
└── debezium-connector                   (KafkaConnector)
```

## Namespaces

- `kafka-cdc` (pre-existing, created by `20-kafka-cluster`)

## Pods

| Pod | Purpose |
|-----|---------|
| `debezium-connect-cluster-connect-0` | Runs the Debezium MySQL connector worker |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `debezium-connect-cluster-connect-api` | 8083 | Kafka Connect REST API |
| `debezium-connect-cluster-connect` | 8083 | Headless service for Connect worker pods |
