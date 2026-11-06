#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/gateway.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/origin.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

NAMESPACE="identity"
REALM="retail-lakehouse"

log::on_success "Keycloak and the platform-gateway login gate are ready"
log::on_failure "Keycloak or the platform-gateway login gate is not ready"

fail() {
  echo "$1" >&2
  exit 1
}

assert_secret_keys() {
  local name=$1 keys
  shift
  # shellcheck disable=SC2016
  keys=$(kubectl get secret "$name" \
    -o go-template='{{range $k, $v := .data}}{{$k}}{{"\n"}}{{end}}' \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}")
  for key in "$@"; do
    grep -qx -- "$key" <<<"$keys" || fail "secret ${NAMESPACE}/${name} has no key ${key}"
  done
}

jwt_payload() {
  jq -R -r '
    split(".")[1]
    | gsub("-"; "+") | gsub("_"; "/")
    | . + ("=" * ((4 - (length % 4)) % 4))
    | @base64d'
}

namespace::assert_ambient "${NAMESPACE}"
gateway::assert_routes_allowed "${NAMESPACE}"

assert_secret_keys keycloak-db username password database
assert_secret_keys keycloak-admin username password
assert_secret_keys keycloak-clients \
  oauth2-proxy-client-secret trino-client-secret \
  platform-validate-client-secret platform-admin-password
assert_secret_keys oauth2-proxy-cookie cookie-secret

for deploy in keycloak-db keycloak oauth2-proxy; do
  kubectl rollout status "deployment/${deploy}" \
    --namespace "${NAMESPACE}" \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
done

mesh::assert_hbone "${NAMESPACE}"

gateway::assert_route_accepted "${NAMESPACE}" keycloak
gateway::assert_route_accepted "${NAMESPACE}" oauth2-proxy

EXPECTED_ISSUER="$(origin::public)/keycloak/realms/${REALM}"

ISSUER="$(gateway::curl "/keycloak/realms/${REALM}/.well-known/openid-configuration" -fsS \
  | jq -r .issuer)"
[[ "${ISSUER}" == "${EXPECTED_ISSUER}" ]] \
  || fail "discovery issuer is '${ISSUER}', expected '${EXPECTED_ISSUER}'"
echo "discovery issuer is ${ISSUER}"

TOKEN="$(gateway::token)"
[[ -n "${TOKEN}" ]] || fail "gateway::token printed an empty token"
PAYLOAD="$(jwt_payload <<<"${TOKEN}")"
unset TOKEN
TOKEN_ISSUER="$(jq -r .iss <<<"${PAYLOAD}")"
[[ "${TOKEN_ISSUER}" == "${EXPECTED_ISSUER}" ]] \
  || fail "token iss is '${TOKEN_ISSUER}', expected '${EXPECTED_ISSUER}'"
jq -e '(.aud | if type == "array" then . else [.] end) | index("oauth2-proxy") != null' \
  <<<"${PAYLOAD}" >/dev/null \
  || fail "token aud does not contain oauth2-proxy"
echo "platform-validate token has iss ${TOKEN_ISSUER} and aud oauth2-proxy"

LOGIN_URL="$(origin::public)/keycloak/realms/${REALM}/protocol/openid-connect/auth"
read -r STATUS LOCATION < <(gateway::curl_anonymous /console/ -s -o /dev/null \
  -w '%{http_code} %{redirect_url}\n') || true
[[ "${STATUS}" == "302" && "${LOCATION}" == "${LOGIN_URL}"* ]] \
  || fail "anonymous /console/ returned '${STATUS} ${LOCATION%%\?*}', expected 302 to ${LOGIN_URL}"
echo "anonymous /console/ is redirected to the Keycloak login"

gateway::curl /console/ -fsS -o /dev/null \
  || fail "/console/ with a platform-validate bearer token did not pass the gate"
echo "/console/ with a platform-validate bearer token passes the gate"

POLARIS_STATUS="$(gateway::curl_anonymous /polaris/api/catalog/v1/config -s -o /dev/null \
  -w '%{http_code}')" || POLARIS_STATUS=000
[[ "${POLARIS_STATUS}" == "401" ]] \
  || fail "anonymous /polaris/api/catalog/v1/config returned ${POLARIS_STATUS}, expected 401"
echo "/polaris is not gated (Polaris answers 401 itself)"

for path in /robots.txt '/robots.txt?x=1' /ping /ready; do
  BUILTIN_STATUS="$(gateway::curl_anonymous "${path}" -s -o /dev/null -w '%{http_code}')" \
    || BUILTIN_STATUS=000
  [[ "${BUILTIN_STATUS}" == "302" || "${BUILTIN_STATUS}" == "403" ]] \
    || fail "anonymous ${path} returned ${BUILTIN_STATUS}, expected 302 or 403 (an oauth2-proxy built-in bypasses the gate)"
done
echo "oauth2-proxy built-in paths outside /sso do not pass the gate"
