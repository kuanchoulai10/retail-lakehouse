# Kafka Cluster

Deploys a KRaft-mode Apache Kafka cluster in the `kafka-cdc` namespace using Strimzi custom resources. The cluster runs three dual-role nodes (controller and broker combined) with a replication factor of 3. This cluster serves as the event backbone for the CDC pipeline between MySQL and the Iceberg lakehouse.

## Deployed Resources

```
Namespace: kafka-cdc
├── kafka-cluster-dual-role-0            (Pod, KafkaNodePool)
├── kafka-cluster-dual-role-1            (Pod, KafkaNodePool)
├── kafka-cluster-dual-role-2            (Pod, KafkaNodePool)
└── kafka-cluster-entity-operator        (Deployment)
```

## Namespaces

- `kafka-cdc`

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
