#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating Prometheus Operator (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/prometheus-operator \
  -n prometheus-operator --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Prometheus Operator is ready."
