#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
KEDA_VERSION="${KEDA_VERSION:-2.18.0}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing KEDA ${KEDA_VERSION} (context: ${KUBE_CONTEXT})"

helm repo add kedacore https://kedacore.github.io/charts
helm repo update kedacore

helm upgrade --install keda kedacore/keda \
  --version "${KEDA_VERSION}" \
  --namespace keda \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
