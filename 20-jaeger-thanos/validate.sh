#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating Jaeger for Thanos (context: ${KUBE_CONTEXT})"

kubectl wait pod \
  -l app.kubernetes.io/managed-by=opentelemetry-operator \
  -n thanos \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

echo "==> Jaeger (thanos) is ready."
