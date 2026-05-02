#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

echo "==> Uninstalling OpenTelemetry Operator (context: ${KUBE_CONTEXT})"

helm uninstall opentelemetry-operator \
  --namespace opentelemetry-operator \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
