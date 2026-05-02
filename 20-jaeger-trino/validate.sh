#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating Jaeger for Trino (context: ${KUBE_CONTEXT})"

kubectl wait pod \
  -l app.kubernetes.io/managed-by=opentelemetry-operator \
  -n trino \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

echo "==> Jaeger (trino) is ready."
