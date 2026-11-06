#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "istiod is ready"
log::on_failure "istiod is not ready"

kubectl rollout status deployment/istiod \
  --namespace istio-system \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

mesh_config="$(kubectl get configmap istio \
  --output jsonpath='{.data.mesh}' \
  --namespace istio-system \
  --context "${KUBE_CONTEXT}")"
grep -Eq '^\s*-?\s*name: oauth2-proxy$' <<<"${mesh_config}" || {
  echo "meshConfig has no extension provider named oauth2-proxy" >&2
  exit 1
}
