#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::header "Validating OpenTelemetry Operator"

kubectl rollout status deployment/opentelemetry-operator \
  -n opentelemetry-operator --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

log::footer "OpenTelemetry Operator is ready"
