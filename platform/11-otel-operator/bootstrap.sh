#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
OTEL_OPERATOR_VERSION="${OTEL_OPERATOR_VERSION:-0.98.0}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing OpenTelemetry Operator ${OTEL_OPERATOR_VERSION} (context: ${KUBE_CONTEXT})"

helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update open-telemetry

helm upgrade --install opentelemetry-operator open-telemetry/opentelemetry-operator \
  --version "${OTEL_OPERATOR_VERSION}" \
  --namespace opentelemetry-operator \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
