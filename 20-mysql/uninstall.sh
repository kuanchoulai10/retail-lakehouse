#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deleting MySQL (context: ${KUBE_CONTEXT})"

kubectl delete -f "$SCRIPT_DIR/mysql.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
