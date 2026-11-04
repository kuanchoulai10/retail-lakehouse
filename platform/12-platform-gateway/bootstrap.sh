#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "platform-gateway installed"
log::on_failure "platform-gateway installation failed"

kubectl create namespace istio-ingress \
  --dry-run=client \
  -o yaml \
  | kubectl apply \
    -f - \
    --context "${KUBE_CONTEXT}"

kubectl apply --server-side \
  -f "$SCRIPT_DIR/gateway.yaml" \
  --context "${KUBE_CONTEXT}"
