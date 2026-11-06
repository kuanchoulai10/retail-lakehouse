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

log::on_success "Keycloak is ready"
log::on_failure "Keycloak is not ready"

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

for deploy in keycloak-db keycloak; do
  kubectl rollout status "deployment/${deploy}" \
    --namespace "${NAMESPACE}" \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
done

mesh::assert_hbone "${NAMESPACE}"

gateway::assert_route_accepted "${NAMESPACE}" keycloak

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
