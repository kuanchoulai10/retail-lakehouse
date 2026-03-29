#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Installing KEDA 2.18.0 (context: ${KUBE_CONTEXT})"

helm repo add kedacore https://kedacore.github.io/charts
helm repo update kedacore

helm upgrade --install keda kedacore/keda \
  --version 2.18.0 \
  --namespace keda \
  --create-namespace \
  --values values.yaml \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
