#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
GATEWAY_API_VERSION="${GATEWAY_API_VERSION:-v1.3.0}"

log::on_success "Gateway API CRDs installed"
log::on_failure "Gateway API CRDs installation failed"

kubectl apply --server-side \
  -f "https://github.com/kubernetes-sigs/gateway-api/releases/download/${GATEWAY_API_VERSION}/standard-install.yaml" \
  --context "${KUBE_CONTEXT}"
