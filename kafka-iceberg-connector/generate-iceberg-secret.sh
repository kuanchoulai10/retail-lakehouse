#!/bin/bash

set -e

echo "Creating Kubernetes secret for Accessing Iceberg Table in AWS S3..."

read -p "  Enter AWS Region: " AWS_REGION
read -p "  Enter AWS Access Key: " AWS_ACCESS_KEY_ID
read -p "  Enter AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY

kubectl create secret generic iceberg-secret \
  --from-literal=awsRegion=$AWS_REGION \
  --from-literal=awsAccessKey=$AWS_ACCESS_KEY_ID \
  --from-literal=awsSecretAccessKey=$AWS_SECRET_ACCESS_KEY \
  --namespace kafka-cdc \
  --dry-run=client -o yaml > "./iceberg-secret.yaml"

echo "iceberg-secret.yaml created."