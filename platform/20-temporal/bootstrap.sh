#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

log::on_success "Temporal namespace deployed"
log::on_failure "Temporal namespace deployment failed"

kubectl create namespace temporal \
  --dry-run=client \
  -o yaml \
  | kubectl apply \
    -f - \
    --context "${KUBE_CONTEXT}"
