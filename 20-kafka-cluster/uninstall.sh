#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Deleting Kafka cluster (context: ${KUBE_CONTEXT})"

kubectl delete -f kafka-cluster.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
