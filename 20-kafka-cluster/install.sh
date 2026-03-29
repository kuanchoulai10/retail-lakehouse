#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Deploying Kafka cluster (context: ${KUBE_CONTEXT})"

kubectl apply -f kafka-cluster.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
