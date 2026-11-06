#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/gateway.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Trino is ready"
log::on_failure "Trino is not ready"

fail() {
  echo "$1" >&2
  exit 1
}

namespace::assert_ambient lakehouse-query-engine

kubectl rollout status deployment/trino-coordinator \
  --namespace lakehouse-query-engine \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/trino-worker \
  --namespace lakehouse-query-engine \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

configmap_json() {
  kubectl get configmap "$1" \
    -o json \
    --namespace lakehouse-query-engine \
    --context "${KUBE_CONTEXT}"
}

configmap_properties() {
  jq -r '.data | to_entries[] | .key as $file | .value | split("\n")[] | "\($file)\t\(.)"'
}

assert_no_google() {
  if grep -q 'accounts.google.com' <<<"$1"; then
    echo "trino-coordinator config.properties still points at accounts.google.com" >&2
    return 1
  fi
}

COORDINATOR_JSON="$(configmap_json trino-coordinator)" \
  || fail "could not read ConfigMap lakehouse-query-engine/trino-coordinator"
WORKER_JSON="$(configmap_json trino-worker)" \
  || fail "could not read ConfigMap lakehouse-query-engine/trino-worker"
CATALOG_JSON="$(configmap_json trino-catalog)" \
  || fail "could not read ConfigMap lakehouse-query-engine/trino-catalog"

configmap_cached() {
  case "$1" in
    trino-coordinator) printf '%s\n' "${COORDINATOR_JSON}" ;;
    trino-worker) printf '%s\n' "${WORKER_JSON}" ;;
    trino-catalog) printf '%s\n' "${CATALOG_JSON}" ;;
    *) fail "unknown ConfigMap $1" ;;
  esac
}

REQUIRED_PROPERTIES=(
  "trino-coordinator config.properties internal-communication.shared-secret"
  "trino-coordinator config.properties http-server.authentication.oauth2.client-secret"
  "trino-worker config.properties internal-communication.shared-secret"
  "trino-catalog iceberg.properties iceberg.rest-catalog.oauth2.credential"
)
for required in "${REQUIRED_PROPERTIES[@]}"; do
  read -r configmap file property <<<"${required}"
  PROPERTIES="$(configmap_cached "${configmap}" | configmap_properties)" \
    || fail "could not parse ConfigMap lakehouse-query-engine/${configmap}"
  grep -q "^${file}"$'\t'"${property}=" <<<"${PROPERTIES}" \
    || fail "${configmap}/${file} has no ${property}"
done
unset PROPERTIES
echo "Trino ConfigMaps set every expected secret property"

SECRET_PROPERTY='(client-secret|shared-secret|\.key|aws-[a-z]+-key|oauth2\.credential)$'
PLAIN_SECRETS=()
for configmap in trino-coordinator trino-worker trino-catalog; do
  while IFS=$'\t' read -r file line; do
    [[ "${line}" == *=* ]] || continue
    property="${line%%=*}"
    value="${line#*=}"
    if [[ "${property}" =~ ${SECRET_PROPERTY} && "${value}" != "\${ENV:"* ]]; then
      PLAIN_SECRETS+=("${configmap}/${file}: ${property}")
    fi
  done < <(configmap_cached "${configmap}" | configmap_properties)
done
unset value
if ((${#PLAIN_SECRETS[@]} > 0)); then
  echo "Trino ConfigMaps hold secret values instead of \${ENV:} references:" >&2
  printf '  %s\n' "${PLAIN_SECRETS[@]}" >&2
  exit 1
fi
echo "Trino ConfigMaps reference every secret through \${ENV:}"

COORDINATOR_CONFIG="$(jq -r '.data["config.properties"] // empty' <<<"${COORDINATOR_JSON}")"
[[ -n "${COORDINATOR_CONFIG}" ]] || fail "trino-coordinator has no config.properties"
assert_no_google "${COORDINATOR_CONFIG}" || exit 1
unset COORDINATOR_CONFIG
echo "trino-coordinator does not point at accounts.google.com"

gateway::assert_routes_allowed lakehouse-query-engine
gateway::assert_route_accepted lakehouse-query-engine trino-ui

ORIGIN="$(gateway::origin)" || fail "public origin unknown"
ENCODED_CALLBACK="$(printf '%s/oauth2/callback' "${ORIGIN}" | jq -sRr @uri)"
UI_RESPONSE="$(gateway::curl /ui/ -s -o /dev/null -w '%{http_code} %{redirect_url}')"
UI_STATUS="${UI_RESPONSE%% *}"
UI_REDIRECT="${UI_RESPONSE#* }"
EXPECTED_AUTH="${ORIGIN}/keycloak/realms/retail-lakehouse/protocol/openid-connect/auth"
if [[ ! "${UI_STATUS}" =~ ^3[0-9][0-9]$ ]] \
  || [[ "${UI_REDIRECT}" != "${EXPECTED_AUTH}"* ]] \
  || ! tr '[:upper:]' '[:lower:]' <<<"${UI_REDIRECT}" \
    | grep -qF "redirect_uri=$(tr '[:upper:]' '[:lower:]' <<<"${ENCODED_CALLBACK}")"; then
  echo "/ui/ did not redirect to the Keycloak login with ${ORIGIN}/oauth2/callback (status ${UI_STATUS})" >&2
  exit 1
fi
echo "/ui/ redirects to the Keycloak login with ${ORIGIN}/oauth2/callback"
