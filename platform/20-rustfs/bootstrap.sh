#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "RustFS deployed"
log::on_failure "RustFS deployment failed"

namespace::apply_ambient object-storage

kubectl apply \
  -f "$SCRIPT_DIR/rustfs-secret.yaml" \
  --context "${KUBE_CONTEXT}"

kubectl apply \
  -f "$SCRIPT_DIR/rustfs.yaml" \
  --context "${KUBE_CONTEXT}"
