#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
OTEL_OPERATOR_VERSION="${OTEL_OPERATOR_VERSION:-0.98.0}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "OpenTelemetry Operator installed"
log::on_failure "OpenTelemetry Operator installation failed"

helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update open-telemetry

helm upgrade --install opentelemetry-operator open-telemetry/opentelemetry-operator \
  --version "${OTEL_OPERATOR_VERSION}" \
  --namespace opentelemetry-operator \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
