# Strimzi Operator

Deploys the Strimzi Kafka Operator via Helm. Strimzi manages the full lifecycle of Apache Kafka clusters, Kafka Connect clusters, topics, users, and connectors on Kubernetes using custom resources. The Kafka cluster and CDC connectors in this stack depend on this operator.

## Deployed Resources

```
Namespace: strimzi-operator
└── strimzi-cluster-operator            (Deployment)
```

## Namespaces

- `strimzi-operator`

## Pods

| Pod | Purpose |
|-----|---------|
| `strimzi-cluster-operator` | Reconciles Kafka and related custom resources |

## CRDs

| CRD | Purpose |
|-----|---------|
| `kafkas.kafka.strimzi.io` | Declares a Kafka cluster |
| `kafkanodepools.kafka.strimzi.io` | Declares a pool of Kafka broker or controller nodes |
| `kafkaconnects.kafka.strimzi.io` | Declares a Kafka Connect cluster |
| `kafkaconnectors.kafka.strimzi.io` | Declares a Kafka connector instance |
| `kafkatopics.kafka.strimzi.io` | Manages Kafka topics declaratively |
| `kafkausers.kafka.strimzi.io` | Manages Kafka users and ACLs |
| `kafkamirrormaker2s.kafka.strimzi.io` | Declares a MirrorMaker 2 replication cluster |
