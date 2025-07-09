#!/bin/bash

set -e

echo "Creating Kubernetes secret for Accessing BigQuery..."

kubectl create secret generic trino-bigquery-secret \
    --from-file=trino-sa.json="$SA_INPUT_PATH" \
    --dry-run=client -o yaml > "./trino-bigquery-secret.yaml"
