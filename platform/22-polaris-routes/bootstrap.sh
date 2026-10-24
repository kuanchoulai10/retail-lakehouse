#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "polaris-routes installed"
log::on_failure "polaris-routes installation failed"

kubectl create namespace istio-ingress \
  --dry-run=client \
  -o yaml \
  | kubectl apply \
    -f - \
    --context "${KUBE_CONTEXT}"

kubectl apply --server-side \
  -f "$SCRIPT_DIR/gateway.yaml" \
  -f "$SCRIPT_DIR/polaris-httproute.yaml" \
  --context "${KUBE_CONTEXT}"
