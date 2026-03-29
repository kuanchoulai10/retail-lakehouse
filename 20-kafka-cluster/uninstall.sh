#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Deleting Kafka cluster (context: ${KUBE_CONTEXT})"

kubectl delete -f kafka-cluster.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
