#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "polaris-routes installed"
log::on_failure "polaris-routes installation failed"

kubectl apply --server-side \
  -f "$SCRIPT_DIR/gateway.yaml" \
  -f "$SCRIPT_DIR/polaris-httproute.yaml" \
  -f "$SCRIPT_DIR/backend-httproute.yaml" \
  --context "${KUBE_CONTEXT}"
