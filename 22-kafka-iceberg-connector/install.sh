#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Deploying Iceberg sink connector (context: ${KUBE_CONTEXT})"

bash generate-iceberg-secret.sh

kubectl apply -f iceberg-secret.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl apply -f iceberg-connect-cluster.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl apply -f iceberg-connector.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
