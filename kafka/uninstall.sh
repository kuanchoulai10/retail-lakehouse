#!/bin/bash

set -e

# Remove Debezium connector and connect cluster
kubectl delete -f debezium-connector.yaml -n kafka-cdc || true
kubectl delete -f debezium-connect-cluster.yaml -n kafka-cdc || true
kubectl delete -f debezium-role-binding.yaml || true
kubectl delete -f debezium-role.yaml || true
kubectl delete -f debezium-secret.yaml || true

# Remove MySQL DB
kubectl delete -f db.yaml -n kafka-cdc || true

# Remove Kafka cluster
kubectl delete -f kafka-cluster.yaml -n kafka-cdc || true

# Uninstall Strimzi operator
helm uninstall strimzi-cluster-operator -n strimzi || true

# Delete namespaces (will remove all resources in them)
kubectl delete namespace kafka-cdc || true
kubectl delete namespace strimzi || true

# Optionally, clean up iceberg resources if used
# kubectl delete -f iceberg-connector.yaml -n kafka-cdc || true
# kubectl delete -f iceberg-connect-cluster.yaml -n kafka-cdc || true
# kubectl delete -f iceberg-secret.yaml -n kafka-cdc || true
