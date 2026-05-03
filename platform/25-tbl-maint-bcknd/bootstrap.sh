#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "table-maintenance backend deployed"
log::on_failure "table-maintenance backend deployment failed"

kubectl apply \
  -f "$SCRIPT_DIR/backend-rbac.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/backend-service.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/backend-deployment.yaml" \
  --context "${KUBE_CONTEXT}"
