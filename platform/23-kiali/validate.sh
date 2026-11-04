#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/gateway.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Kiali is ready"
log::on_failure "Kiali is not ready"

kubectl rollout status deployment/kiali \
  --namespace istio-system \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

gateway::assert_routes_allowed istio-system
gateway::assert_route_accepted istio-system kiali
gateway::curl kiali.localhost /api/status -fsS -o /dev/null
