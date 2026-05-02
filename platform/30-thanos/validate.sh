#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Thanos is ready"
log::on_failure "Thanos is not ready"

kubectl rollout status deployment/thanos-query \
  --namespace thanos \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/thanos-query-frontend \
  --namespace thanos \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/thanos-receive-router \
  --namespace thanos \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
