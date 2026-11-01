# Kafka Cluster

Deploys a KRaft-mode Apache Kafka cluster in the `kafka` namespace using Strimzi custom resources. The cluster runs three dual-role nodes (controller and broker combined) with a replication factor of 3. This cluster serves as the event backbone for the CDC pipeline between MySQL and the Iceberg lakehouse.

## Deployed Resources

```
Namespace: kafka
├── kafka-cluster-dual-role-0            (Pod, KafkaNodePool)
├── kafka-cluster-dual-role-1            (Pod, KafkaNodePool)
├── kafka-cluster-dual-role-2            (Pod, KafkaNodePool)
└── kafka-cluster-entity-operator        (Deployment)
```

## Namespaces

- `kafka`

## Pods

| Pod | Purpose |
|-----|---------|
| `kafka-cluster-dual-role-{0,1,2}` | Kafka broker and KRaft controller nodes |
| `kafka-cluster-entity-operator` | Manages KafkaTopic and KafkaUser resources |

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `kafka-cluster-kafka-bootstrap` | 9092 (PLAINTEXT), 9093 (TLS), 9091 (replication) | Client connection entry point |
| `kafka-cluster-kafka-brokers` | 9090, 9091, 9092, 9093, 8443 | Headless service for broker-to-broker communication |

## Memory

The `dual-role` node pool sets the JVM heap to `-Xms1g -Xmx1g`, the pod memory limit to `2560Mi` (heap plus page cache and off-heap headroom) and the request to `1536Mi`. The request is sized from usage, not set equal to the limit: with request = limit on Kafka, both KafkaConnects, RustFS and Jaeger the node had 27013Mi of 28005Mi allocatable requested, and Spark maintenance executors (1433Mi each) could not be scheduled.

Measured on the deployed configuration (2026-11-01, after a clean onboard, a table maintenance `e2e.sh` run and a 30 minute soak with no changes, 14:05–14:35): the brokers used 675 / 751 / 678 MiB with no restart. Before the limit they were unbounded and used about 3.7 / 3.4 / 1.9 GiB. Check there is no under-replicated partition after a roll with `kafka-topics.sh --describe --under-replicated-partitions` inside a broker pod.
