#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Root app is Healthy"
log::on_failure "Root app is not Healthy"

kubectl wait application/root-app \
  --namespace argocd \
  --for=jsonpath='{.status.health.status}'=Healthy \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
