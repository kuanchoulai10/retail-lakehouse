#!/bin/bash

set -e

# Deploy Strimzi Cluster Operator
kubectl create namespace strimzi
kubectl create namespace kafka-cdc

helm repo add strimzi https://strimzi.io/charts/
helm install \
  strimzi-cluster-operator \
  oci://quay.io/strimzi-helm/strimzi-kafka-operator \
  -f values.yaml \
  -n strimzi \
  --version 0.46.1
sleep 5
kubectl wait --for=condition=Ready pod -l name=strimzi-cluster-operator -n strimzi --timeout=1200s

# Deploy Kafka cluster using Strimzi
kubectl apply -f kafka-cluster.yaml -n kafka-cdc
sleep 5
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=kafka -n kafka-cdc --timeout=1200s
sleep 5
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=entity-operator -n kafka-cdc --timeout=1200s
