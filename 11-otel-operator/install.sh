#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing OpenTelemetry Operator 0.98.0 (context: ${KUBE_CONTEXT})"

helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update open-telemetry

helm upgrade --install opentelemetry-operator open-telemetry/opentelemetry-operator \
  --version 0.98.0 \
  --namespace opentelemetry-operator \
  --create-namespace \
  --values values.yaml \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
