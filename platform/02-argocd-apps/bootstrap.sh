#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "ArgoCD root app applied. ArgoCD will now reconcile all child applications."
log::on_failure "ArgoCD root app apply failed"

kubectl apply \
  -f "$SCRIPT_DIR/root-app.yaml" \
  --context "${KUBE_CONTEXT}"
