#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Lakehouse control plane namespaces are ready"
log::on_failure "Lakehouse control plane namespaces are not ready"

for namespace in lakehouse-control-plane lakehouse-maintenance-operations; do
  kubectl wait "namespace/${namespace}" \
    --for jsonpath='{.status.phase}'=Active \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
done
