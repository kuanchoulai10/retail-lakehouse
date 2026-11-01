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

The KafkaConnect has a memory request of `896Mi` and a limit of `1Gi` with heap `-Xms512m -Xmx512m`. The request is sized from usage, not set equal to the limit: with request = limit on Kafka, both KafkaConnects, RustFS and Jaeger the node had 27013Mi of 28005Mi allocatable requested, and Spark maintenance executors (1433Mi each) could not be scheduled.

Measured on the deployed configuration (2026-11-01, after a clean onboard, a table maintenance `e2e.sh` run and a 30 minute soak with no changes, 14:05–14:35): 739 MiB, no restart, which leaves about 285 MiB below the limit; raise the limit to 1280Mi if it restarts. It had no limit and an unset heap before and used about 537 MiB.
