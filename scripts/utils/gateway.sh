#!/usr/bin/env bash
# shellcheck disable=SC2154
# platform-gateway helpers. Every function reads KUBE_CONTEXT.
#
#   gateway::allow_routes <namespace>             # label the namespace so its HTTPRoutes may attach
#   gateway::assert_routes_allowed <namespace>    # fail unless the namespace carries that label
#   gateway::assert_route_accepted <ns> <route>   # wait until the HTTPRoute is Accepted (TIMEOUT)
#   gateway::curl <path> [curl args]              # curl a path through the gateway with a
#                                                 # platform-validate bearer token; anonymous only
#                                                 # while identity/keycloak-clients does not exist.
#                                                 # Fails when no token is obtained, or when the gate
#                                                 # still redirects to the Keycloak login for oauth2-proxy (redirect_uri = <origin>/sso/callback)
#   gateway::curl_anonymous <path> [curl args]    # the same call, never with a token
#   gateway::token                                # print a platform-validate access token
#   gateway::origin                               # print the deployed public origin (ConfigMap
#                                                 # identity/public-origin, key origin); origin::public
#                                                 # only while that ConfigMap does not exist
#   gateway::assert_redirect_uri <client> <uri>   # fail unless the Keycloak realm accepts <uri> as a
#                                                 # redirect_uri of <client> (anonymous auth request: 200)

[[ -n "${__GATEWAY_SH_LOADED:-}" ]] && return 0
__GATEWAY_SH_LOADED=1

source "$(dirname "${BASH_SOURCE[0]}")/origin.sh"

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

__gateway::has_clients_secret() {
  [[ -n "$(kubectl get secret keycloak-clients \
    --ignore-not-found \
    -o name \
    --namespace identity \
    --context "${KUBE_CONTEXT}")" ]]
}

gateway::origin() {
  local configmap origin
  configmap=$(kubectl get configmap public-origin \
    --ignore-not-found \
    -o json \
    --namespace identity \
    --context "${KUBE_CONTEXT}") || {
    echo "gateway::origin: could not read ConfigMap identity/public-origin" >&2
    return 1
  }
  if [[ -z "$configmap" ]]; then
    origin=$(origin::public) || return 1
  else
    origin=$(jq -r '.data.origin // empty' <<<"$configmap")
    if [[ -z "$origin" ]]; then
      echo "gateway::origin: ConfigMap identity/public-origin has no origin" >&2
      return 1
    fi
  fi
  printf '%s\n' "${origin%/}"
}

gateway::assert_redirect_uri() {
  local client=$1 redirect_uri=$2 encoded status
  encoded=$(printf '%s' "$redirect_uri" | jq -sRr @uri)
  status=$(gateway::curl_anonymous \
    "/keycloak/realms/retail-lakehouse/protocol/openid-connect/auth?client_id=${client}&response_type=code&scope=openid&redirect_uri=${encoded}" \
    -s -o /dev/null -w '%{http_code}') || status=000
  if [[ "$status" != "200" ]]; then
    echo "Keycloak answered ${status} to an auth request of client ${client} with redirect_uri ${redirect_uri}, expected 200 (400 means the realm does not list that redirect URI)" >&2
    return 1
  fi
}

__gateway::login_url() {
  local origin
  origin=$(gateway::origin) || return 1
  printf '%s/keycloak/realms/retail-lakehouse/protocol/openid-connect/auth\n' "$origin"
}

__gateway::proxy_callback() {
  local origin
  origin=$(gateway::origin) || return 1
  printf '%s/sso/callback' "$origin" | jq -sRr @uri
}

__gateway::free_fd() {
  local fd
  for fd in $(seq 10 99); do
    [[ -e "/dev/fd/${fd}" ]] || { printf '%s\n' "$fd"; return 0; }
  done
  return 1
}

gateway::curl() {
  local path=$1 token login_url callback fd headers rc=0
  shift
  if ! __gateway::has_clients_secret; then
    __gateway::request "$path" "$@"
    return
  fi
  if ! token=$(gateway::token); then
    echo "gateway::curl: identity/keycloak-clients exists but no platform-validate token was obtained for ${path}" >&2
    return 1
  fi
  if ! login_url=$(__gateway::login_url) || ! callback=$(__gateway::proxy_callback); then
    echo "gateway::curl: public origin unknown, cannot recognise a redirect to the Keycloak login" >&2
    return 1
  fi
  fd=$(__gateway::free_fd) || { echo "gateway::curl: no free file descriptor" >&2; return 1; }
  headers=$(mktemp)
  eval "exec ${fd}< <(printf 'Authorization: Bearer %s\\n' \"\$token\")"
  unset token
  __gateway::request "$path" -H "@/dev/fd/${fd}" -D "$headers" "$@" || rc=$?
  eval "exec ${fd}<&-"
  if tr -d '\r' <"$headers" \
    | awk -v url="$login_url" -v callback="redirect_uri=${callback}" '
      {location = tolower($2)}
      tolower($1) == "location:" && index(location, tolower(url)) == 1 && index(location, tolower(callback)) > 0 {found = 1}
      END {exit !found}'; then
    echo "gateway::curl: ${path} was redirected to the oauth2-proxy login although a platform-validate token was sent (the gate rejected it)" >&2
    rm -f "$headers"
    return 1
  fi
  rm -f "$headers"
  return "$rc"
}

gateway::curl_anonymous() {
  __gateway::request "$@"
}

gateway::token() {
  local secret response token
  if ! __gateway::has_clients_secret; then
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
