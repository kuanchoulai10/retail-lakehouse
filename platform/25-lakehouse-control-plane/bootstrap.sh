#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

log::on_success "Lakehouse control plane namespaces deployed"
log::on_failure "Lakehouse control plane namespaces deployment failed"

for namespace in lakehouse-control-plane lakehouse-maintenance-operations; do
  kubectl create namespace "${namespace}" \
    --dry-run=client \
    -o yaml \
    | kubectl apply \
      -f - \
      --context "${KUBE_CONTEXT}"
done
