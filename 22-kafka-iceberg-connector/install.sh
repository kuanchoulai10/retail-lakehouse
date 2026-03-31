#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying Iceberg sink connector (context: ${KUBE_CONTEXT})"

sops --decrypt "$SCRIPT_DIR/iceberg-secret.yaml" \
  | kubectl apply -f - -n kafka-cdc --context "${KUBE_CONTEXT}"

kubectl apply -f "$SCRIPT_DIR/iceberg-connect-cluster.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/iceberg-connector.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
