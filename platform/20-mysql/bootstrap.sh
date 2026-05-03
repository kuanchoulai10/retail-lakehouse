#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying MySQL (context: ${KUBE_CONTEXT})"

kubectl create namespace kafka-cdc --dry-run=client -o yaml \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

kubectl apply -f "$SCRIPT_DIR/mysql-secret.yaml" --context "${KUBE_CONTEXT}"

kubectl apply -f "$SCRIPT_DIR/mysql.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
