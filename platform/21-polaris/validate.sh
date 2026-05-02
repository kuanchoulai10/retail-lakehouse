#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Polaris is ready"
log::on_failure "Polaris is not ready"

kubectl rollout status deployment/polaris \
  --namespace polaris \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
