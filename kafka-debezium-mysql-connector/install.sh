#!/bin/bash

set -e

# Deploy Debezium Connect Cluster
kubectl apply -f debezium-secret.yaml
kubectl apply -f debezium-role.yaml
kubectl apply -f debezium-role-binding.yaml
kubectl apply -f debezium-connect-cluster.yaml -n kafka-cdc
sleep 5
kubectl logs pod/debezium-connect-cluster-connect-build -n kafka-cdc -f
sleep 5
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=kafka-connect -n kafka-cdc --timeout=1200s

kubectl apply -f debezium-connector.yaml -n kafka-cdc
kubectl get kafkaconnector -n kafka-cdc