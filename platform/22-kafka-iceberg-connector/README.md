# Iceberg Sink Connector

Deploys a Strimzi KafkaConnect cluster with the Iceberg Kafka Connect sink plugin installed. The connector consumes CDC events from Kafka and writes them as Apache Iceberg tables in the S3-compatible MinIO warehouse, using AWS Glue as the Iceberg catalog.

## Deployed Resources

```
Namespace: kafka-cdc
├── iceberg-connect-cluster-connect-0    (Pod, KafkaConnect)
└── iceberg-connector                    (KafkaConnector)
```

## Namespaces

- `kafka-cdc` (pre-existing, created by `20-kafka-cluster`)

## Pods

| Pod | Purpose |
|-----|---------|
| `iceberg-connect-cluster-connect-0` | Runs the Iceberg sink connector worker |
