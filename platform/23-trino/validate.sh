#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Trino is ready"
log::on_failure "Trino is not ready"

namespace::assert_ambient lakehouse-query-engine

kubectl rollout status deployment/trino-coordinator \
  --namespace lakehouse-query-engine \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/trino-worker \
  --namespace lakehouse-query-engine \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

configmap_properties() {
  kubectl get configmap "$1" \
    -o json \
    --namespace lakehouse-query-engine \
    --context "${KUBE_CONTEXT}" \
    | jq -r '.data | to_entries[] | .key as $file | .value | split("\n")[] | "\($file)\t\(.)"'
}

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
  done < <(configmap_properties "${configmap}")
done
unset value
if ((${#PLAIN_SECRETS[@]} > 0)); then
  echo "Trino ConfigMaps hold secret values instead of \${ENV:} references:" >&2
  printf '  %s\n' "${PLAIN_SECRETS[@]}" >&2
  exit 1
fi

if kubectl get configmap trino-coordinator \
  -o jsonpath='{.data.config\.properties}' \
  --namespace lakehouse-query-engine \
  --context "${KUBE_CONTEXT}" \
  | grep -q 'accounts.google.com'; then
  echo "trino-coordinator config.properties still points at accounts.google.com" >&2
  exit 1
fi

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/gateway.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/origin.sh"

gateway::assert_routes_allowed lakehouse-query-engine
gateway::assert_route_accepted lakehouse-query-engine trino-ui

ORIGIN="$(origin::public)"
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
