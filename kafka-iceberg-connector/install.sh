#!/bin/bash

set -e

kubectl apply -f iceberg-secret.yaml -n kafka-cdc
kubectl apply -f iceberg-connect-cluster.yaml -n kafka-cdc
kubectl apply -f iceberg-connector.yaml -n kafka-cdc
