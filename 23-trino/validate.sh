#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Trino is ready"
log::on_failure "Trino is not ready"

kubectl rollout status deployment/trino-coordinator \
  --namespace trino \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/trino-worker \
  --namespace trino \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
