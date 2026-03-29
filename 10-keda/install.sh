#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing KEDA 2.18.0 (context: ${KUBE_CONTEXT})"

helm repo add kedacore https://kedacore.github.io/charts
helm repo update kedacore

helm upgrade --install keda kedacore/keda \
  --version 2.18.0 \
  --namespace keda \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
