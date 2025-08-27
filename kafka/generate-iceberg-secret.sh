#!/bin/bash

set -e

echo "Creating Kubernetes secret for Accessing Iceberg Table in AWS S3..."

kubectl create secret generic iceberg-secret \
  --from-literal=awsAccessKey=$AWS_ACCESS_KEY_ID \
  --from-literal=awsSecretAccessKey=$AWS_SECRET_ACCESS_KEY \
  --from-literal=awsRegion=$AWS_ICEBERG_REGION \
  --namespace kafka-cdc \
  --dry-run=client -o yaml > "./iceberg-secret.yaml"
