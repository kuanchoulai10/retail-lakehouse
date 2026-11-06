#!/usr/bin/env bash
# shellcheck disable=SC2154
# platform-gateway helpers. Every function reads KUBE_CONTEXT.
#
#   gateway::allow_routes <namespace>             # label the namespace so its HTTPRoutes may attach
#   gateway::assert_routes_allowed <namespace>    # fail unless the namespace carries that label
#   gateway::assert_route_accepted <ns> <route>   # wait until the HTTPRoute is Accepted (TIMEOUT)
#   gateway::curl <path> [curl args]              # curl a path through the gateway
#   gateway::token                                # print a platform-validate access token

[[ -n "${__GATEWAY_SH_LOADED:-}" ]] && return 0
__GATEWAY_SH_LOADED=1

GATEWAY_ROUTES_LABEL="retail-lakehouse.io/gateway-routes"

gateway::allow_routes() {
  local name=$1
  kubectl apply --server-side \
    --field-manager platform-gateway-routes \
    -f - \
    --context "${KUBE_CONTEXT}" <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: ${name}
  labels:
    ${GATEWAY_ROUTES_LABEL}: allowed
EOF
}

gateway::assert_routes_allowed() {
  local name=$1 value
  value=$(kubectl get namespace "$name" \
    -o jsonpath='{.metadata.labels.retail-lakehouse\.io/gateway-routes}' \
    --context "${KUBE_CONTEXT}")
  if [[ "$value" != "allowed" ]]; then
    echo "namespace $name is missing label ${GATEWAY_ROUTES_LABEL}=allowed (found '${value}')" >&2
    return 1
  fi
}

gateway::assert_route_accepted() {
  local namespace=$1 route=$2
  kubectl wait "httproute/${route}" \
    --for=jsonpath='{.status.parents[0].conditions[?(@.type=="Accepted")].status}'=True \
    --namespace "$namespace" \
    --timeout "${TIMEOUT:-300s}" \
    --context "${KUBE_CONTEXT}"
}

__gateway::request() {
  local path=$1 pf_pid pf_log port=""
  shift
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
  curl --max-time 10 "$@" "http://127.0.0.1:${port}${path}"
}

gateway::curl() {
  __gateway::request "$@"
}

gateway::token() {
  local secret response token
  if [[ -z "$(kubectl get secret keycloak-clients \
    --ignore-not-found \
    -o name \
    --namespace identity \
    --context "${KUBE_CONTEXT}")" ]]; then
    echo "secret identity/keycloak-clients does not exist" >&2
    return 1
  fi
  secret=$(kubectl get secret keycloak-clients \
    -o jsonpath='{.data.platform-validate-client-secret}' \
    --namespace identity \
    --context "${KUBE_CONTEXT}" | base64 -d)
  if [[ -z "$secret" ]]; then
    echo "secret identity/keycloak-clients has an empty platform-validate-client-secret" >&2
    return 1
  fi
  response=$(printf 'grant_type=client_credentials&client_id=platform-validate&client_secret=%s' "$secret" \
    | __gateway::request /keycloak/realms/retail-lakehouse/protocol/openid-connect/token \
      -fsS --data @-) || return 1
  token=$(jq -r '.access_token // empty' <<<"$response")
  if [[ -z "$token" ]]; then
    echo "the token endpoint returned no access_token" >&2
    return 1
  fi
  printf '%s\n' "$token"
}
