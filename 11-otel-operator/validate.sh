#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating OpenTelemetry Operator (context: ${KUBE_CONTEXT})"

kubectl rollout status deployment/opentelemetry-operator \
  -n opentelemetry-operator --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> OpenTelemetry Operator is ready."
