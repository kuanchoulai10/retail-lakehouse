#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deleting Kafka cluster (context: ${KUBE_CONTEXT})"

kubectl delete -f "$SCRIPT_DIR/kafka-cluster.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
