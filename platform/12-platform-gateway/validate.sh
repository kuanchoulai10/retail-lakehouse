#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "platform-gateway is Programmed"
log::on_failure "platform-gateway is not Programmed"

kubectl wait --for=condition=Programmed gateway/platform-gateway \
  --namespace istio-ingress \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/platform-gateway-istio \
  --namespace istio-ingress \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
