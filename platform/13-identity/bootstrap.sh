#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/gateway.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/origin.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-600s}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="identity"

log::on_success "Keycloak, oauth2-proxy and the platform-gateway login gate deployed"
log::on_failure "Keycloak, oauth2-proxy or the login gate deployment failed"

fail() {
  echo "$1" >&2
  exit 1
}

secret_exists() {
  [[ -n "$(kubectl get secret "$1" \
    --ignore-not-found \
    -o name \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}")" ]]
}

random_hex() {
  local value
  value="$(openssl rand -hex 32)"
  [[ -n "${value}" ]] || fail "openssl generated an empty value"
  printf '%s' "${value}"
}

random_cookie_secret() {
  local value
  value="$(openssl rand -base64 32 | tr -- '+/' '-_')"
  [[ -n "${value}" ]] || fail "openssl generated an empty cookie secret"
  printf '%s' "${value}"
}

create_secret() {
  local name=$1
  shift
  kubectl create secret generic "${name}" \
    "$@" \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" >/dev/null
  echo "secret ${NAMESPACE}/${name} created"
}

ORIGIN="$(origin::public)" || fail "public origin unknown"

namespace::apply_ambient "${NAMESPACE}"
gateway::allow_routes "${NAMESPACE}"

if ! secret_exists keycloak-db; then
  DB_PASSWORD="$(random_hex)"
  create_secret keycloak-db \
    --from-literal=username=keycloak \
    --from-literal=database=keycloak \
    --from-file=password=<(printf '%s' "${DB_PASSWORD}")
  unset DB_PASSWORD
fi

if ! secret_exists keycloak-admin; then
  ADMIN_PASSWORD="$(random_hex)"
  create_secret keycloak-admin \
    --from-literal=username=admin \
    --from-file=password=<(printf '%s' "${ADMIN_PASSWORD}")
  unset ADMIN_PASSWORD
fi

if ! secret_exists keycloak-clients; then
  OAUTH2_PROXY_CLIENT_SECRET="$(random_hex)"
  TRINO_CLIENT_SECRET="$(random_hex)"
  PLATFORM_VALIDATE_CLIENT_SECRET="$(random_hex)"
  PLATFORM_ADMIN_PASSWORD="$(random_hex)"
  create_secret keycloak-clients \
    --from-file=oauth2-proxy-client-secret=<(printf '%s' "${OAUTH2_PROXY_CLIENT_SECRET}") \
    --from-file=trino-client-secret=<(printf '%s' "${TRINO_CLIENT_SECRET}") \
    --from-file=platform-validate-client-secret=<(printf '%s' "${PLATFORM_VALIDATE_CLIENT_SECRET}") \
    --from-file=platform-admin-password=<(printf '%s' "${PLATFORM_ADMIN_PASSWORD}")
  unset OAUTH2_PROXY_CLIENT_SECRET TRINO_CLIENT_SECRET \
    PLATFORM_VALIDATE_CLIENT_SECRET PLATFORM_ADMIN_PASSWORD
fi

if ! secret_exists oauth2-proxy-cookie; then
  COOKIE_SECRET="$(random_cookie_secret)"
  create_secret oauth2-proxy-cookie \
    --from-file=cookie-secret=<(printf '%s' "${COOKIE_SECRET}")
  unset COOKIE_SECRET
fi

PREVIOUS_ORIGIN="$(kubectl get configmap public-origin \
  --ignore-not-found \
  -o jsonpath='{.data.origin}' \
  --namespace "${NAMESPACE}" \
  --context "${KUBE_CONTEXT}")"

kubectl apply --server-side \
  --field-manager identity-bootstrap \
  -f - \
  --context "${KUBE_CONTEXT}" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: public-origin
  namespace: ${NAMESPACE}
  labels:
    app.kubernetes.io/name: keycloak
    app.kubernetes.io/instance: public-origin
    app.kubernetes.io/component: config
    app.kubernetes.io/part-of: identity
    app.kubernetes.io/managed-by: kubectl
data:
  origin: ${ORIGIN}
EOF

for manifest in keycloak-db-pvc keycloak-db-deployment keycloak-db-service; do
  kubectl apply \
    -f "${SCRIPT_DIR}/${manifest}.yaml" \
    --context "${KUBE_CONTEXT}"
done

kubectl rollout status deployment/keycloak-db \
  --namespace "${NAMESPACE}" \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

for manifest in keycloak-realm-configmap keycloak-deployment keycloak-service; do
  kubectl apply \
    -f "${SCRIPT_DIR}/${manifest}.yaml" \
    --context "${KUBE_CONTEXT}"
done

ORIGIN_CHANGED=false
if [[ -n "${PREVIOUS_ORIGIN}" && "${PREVIOUS_ORIGIN}" != "${ORIGIN}" ]]; then
  ORIGIN_CHANGED=true
fi

if [[ "${ORIGIN_CHANGED}" == true ]]; then
  echo "public origin changed from ${PREVIOUS_ORIGIN} to ${ORIGIN}: restarting Keycloak"
  echo "the realm keeps its old redirect URIs; update them by hand (see README)"
  kubectl rollout restart deployment/keycloak \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}"
fi

kubectl apply \
  -f "${SCRIPT_DIR}/keycloak-route.yaml" \
  --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/keycloak \
  --namespace "${NAMESPACE}" \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

for manifest in oauth2-proxy-deployment oauth2-proxy-service oauth2-proxy-route; do
  kubectl apply \
    -f "${SCRIPT_DIR}/${manifest}.yaml" \
    --context "${KUBE_CONTEXT}"
done

if [[ "${ORIGIN_CHANGED}" == true ]]; then
  echo "public origin changed: restarting oauth2-proxy"
  kubectl rollout restart deployment/oauth2-proxy \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}"
fi

kubectl rollout status deployment/oauth2-proxy \
  --namespace "${NAMESPACE}" \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

for manifest in platform-gateway-sso-builtins-policy platform-gateway-sso-policy; do
  kubectl apply \
    -f "${SCRIPT_DIR}/${manifest}.yaml" \
    --context "${KUBE_CONTEXT}"
done
