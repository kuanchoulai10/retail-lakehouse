#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "istio-base is ready"
log::on_failure "istio-base is not ready"

for crd in \
  virtualservices.networking.istio.io \
  gateways.networking.istio.io \
  destinationrules.networking.istio.io \
  peerauthentications.security.istio.io \
  authorizationpolicies.security.istio.io; do
  kubectl wait --for=condition=Established "crd/${crd}" \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
done
