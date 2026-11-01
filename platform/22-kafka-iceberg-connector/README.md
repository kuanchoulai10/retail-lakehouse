# Iceberg Sink Connector

Deploys a Strimzi KafkaConnect cluster with the Iceberg Kafka Connect sink plugin installed. The connector consumes CDC events from Kafka and writes them as Apache Iceberg tables in the S3-compatible RustFS warehouse, using AWS Glue as the Iceberg catalog.

## Deployed Resources

```
Namespace: kafka
├── iceberg-connect-cluster-connect-0    (Pod, KafkaConnect)
└── iceberg-connector                    (KafkaConnector)
```

## Namespaces

- `kafka` (pre-existing, created by `20-kafka-cluster`)

## Pods

| Pod | Purpose |
|-----|---------|
| `iceberg-connect-cluster-connect-0` | Runs the Iceberg sink connector worker |

## Memory

The KafkaConnect has a memory limit of `1Gi` and a request of `896Mi` (it used 767 MiB after a 30 minute soak) with heap `-Xms512m -Xmx512m`. The request is sized from usage, not set equal to the limit: with request = limit on Kafka, both KafkaConnects, RustFS and Jaeger the node had 27013Mi of 28005Mi allocatable requested, and Spark maintenance executors (1433Mi each) could not be scheduled. It had no limit and an unset heap before, and used about 537 MiB; after the change it uses about 780 MiB, which leaves about 240 MiB below the limit.
