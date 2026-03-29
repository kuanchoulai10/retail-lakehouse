#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Strimzi Operator 0.46.1 (context: ${KUBE_CONTEXT})"

helm repo add strimzi https://strimzi.io/charts/
helm repo update strimzi

helm upgrade --install strimzi-operator strimzi/strimzi-kafka-operator \
  --version 0.46.1 \
  --namespace strimzi-operator \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
