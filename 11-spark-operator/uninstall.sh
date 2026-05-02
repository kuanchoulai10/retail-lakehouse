#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

echo "==> Uninstalling Spark Operator (context: ${KUBE_CONTEXT})"

helm uninstall spark-operator \
  --namespace spark-operator \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
