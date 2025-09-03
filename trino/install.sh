#!/bin/bash

set -euo pipefail

# --8<-- [start:env]
# 產生 .env 和 values.yaml 檔案
bash generate-env.sh
# --8<-- [end:env]


# 載入 .env 當作環境變數
set -a
# shellcheck disable=SC1090
source ".env"
set +a

kubectl create namespace trino || true

# --8<-- [start:tls]
bash generate-tls-certs.sh
kubectl apply -f ./trino-tls-secret.yaml -n trino
# --8<-- [end:tls]

# --8<-- [start:bq]
echo "Generating Kubernetes secret for Accessing BigQuery..."
kubectl create secret generic trino-bigquery-secret \
    --from-file=trino-sa.json="$GCP_SA_INPUT_PATH" \
    --dry-run=client -o yaml > "./trino-bigquery-secret.yaml"
echo "trino-bigquery-secret.yaml generated successfully."
kubectl apply -f ./trino-bigquery-secret.yaml -n trino
# --8<-- [end:bq]

# --8<-- [start:helm]
helm repo add trino https://trinodb.github.io/charts/
helm repo update
helm install trino trino/trino \
  -f values.yaml \
  -n trino \
  --version 1.39.1 \
# --8<-- [end:helm]