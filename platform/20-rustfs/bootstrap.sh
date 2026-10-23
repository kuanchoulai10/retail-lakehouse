#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "RustFS deployed"
log::on_failure "RustFS deployment failed"

kubectl create namespace object-storage \
  --dry-run=client \
  -o yaml \
  | kubectl apply \
    -f - \
    --context "${KUBE_CONTEXT}"

kubectl apply \
  -f "$SCRIPT_DIR/rustfs-secret.yaml" \
  --context "${KUBE_CONTEXT}"

kubectl apply \
  -f "$SCRIPT_DIR/rustfs.yaml" \
  --context "${KUBE_CONTEXT}"
