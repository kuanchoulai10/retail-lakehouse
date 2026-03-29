#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Deleting MySQL (context: ${KUBE_CONTEXT})"

kubectl delete -f mysql.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
