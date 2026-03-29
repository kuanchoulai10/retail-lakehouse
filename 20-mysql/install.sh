#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Deploying MySQL (context: ${KUBE_CONTEXT})"

kubectl apply -f mysql.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
