#!/bin/bash

set -e

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

echo "Creating Kubernetes secret for MinIO S3 access..."

kubectl create secret generic iceberg-secret \
  --from-literal=awsAccessKey=minio_user \
  --from-literal=awsSecretAccessKey=minio_password \
  --namespace kafka-cdc \
  --dry-run=client -o yaml \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

echo "iceberg-secret applied."
