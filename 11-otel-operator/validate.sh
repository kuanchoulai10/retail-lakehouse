#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "OpenTelemetry Operator is ready"
log::on_failure "OpenTelemetry Operator is not ready"

kubectl rollout status deployment/opentelemetry-operator \
  --namespace opentelemetry-operator \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
