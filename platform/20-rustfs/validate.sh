#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "RustFS is ready"
log::on_failure "RustFS is not ready"

namespace::assert_ambient object-storage

kubectl rollout status deployment/rustfs \
  --namespace object-storage \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
