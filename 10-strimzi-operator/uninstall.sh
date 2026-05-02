#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

echo "==> Uninstalling Strimzi Operator (context: ${KUBE_CONTEXT})"

helm uninstall strimzi-operator \
  --namespace strimzi-operator \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
