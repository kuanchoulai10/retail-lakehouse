#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Kiali is ready"
log::on_failure "Kiali is not ready"

assert_kiali_status_through_gateway() {
  local pf_pid pf_log port="" status
  pf_log=$(mktemp)
  kubectl port-forward service/platform-gateway-istio :80 \
    --namespace istio-ingress \
    --context "${KUBE_CONTEXT}" >"$pf_log" 2>&1 &
  pf_pid=$!
  # shellcheck disable=SC2064
  trap "kill $pf_pid 2>/dev/null || true; wait $pf_pid 2>/dev/null || true; rm -f '$pf_log'; trap - RETURN" RETURN
  for _ in $(seq 1 50); do
    port=$(sed -n 's/^Forwarding from 127\.0\.0\.1:\([0-9]*\) ->.*/\1/p' "$pf_log" | head -n 1)
    [[ -n "$port" ]] && break
    kill -0 "$pf_pid" 2>/dev/null || break
    sleep 0.1
  done
  if [[ -z "$port" ]]; then
    echo "port-forward to platform-gateway-istio did not start" >&2
    cat "$pf_log" >&2
    return 1
  fi
  status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:${port}/kiali/api/status") || status=000
  if [[ "$status" != "200" ]]; then
    echo "GET /kiali/api/status returned ${status}" >&2
    return 1
  fi
}

kubectl rollout status deployment/kiali \
  --namespace istio-system \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait --for=jsonpath='{.status.parents[0].conditions[?(@.type=="Accepted")].status}'=True httproute/kiali \
  --namespace istio-system \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

assert_kiali_status_through_gateway
