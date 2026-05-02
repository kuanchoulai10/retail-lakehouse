#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deleting Iceberg sink connector (context: ${KUBE_CONTEXT})"

kubectl delete -f "$SCRIPT_DIR/iceberg-connector.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl delete -f "$SCRIPT_DIR/iceberg-connect-cluster.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl delete -f "$SCRIPT_DIR/iceberg-secret.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
