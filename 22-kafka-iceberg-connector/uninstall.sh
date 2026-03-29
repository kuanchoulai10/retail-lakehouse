#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Deleting Iceberg sink connector (context: ${KUBE_CONTEXT})"

kubectl delete -f iceberg-connector.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl delete -f iceberg-connect-cluster.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl delete -f iceberg-secret.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
