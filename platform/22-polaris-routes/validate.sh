#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "polaris-routes are Programmed"
log::on_failure "polaris-routes are not Programmed"

kubectl wait --for=condition=Programmed gateway/platform-gateway \
  --namespace istio-ingress \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait --for=jsonpath='{.status.parents[0].conditions[?(@.type=="Accepted")].status}'=True httproute/polaris-catchall \
  --namespace polaris \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait --for=jsonpath='{.status.parents[0].conditions[?(@.type=="Accepted")].status}'=True httproute/backend-route \
  --namespace polaris \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
