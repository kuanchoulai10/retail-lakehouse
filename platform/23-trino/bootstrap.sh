#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/origin.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TRINO_VERSION="${TRINO_VERSION:-1.39.1}"
TIMEOUT="${TIMEOUT:-120s}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NAMESPACE="lakehouse-query-engine"

log::on_success "Trino ${TRINO_VERSION} installed"
log::on_failure "Trino installation failed"

fail() {
  echo "$1" >&2
  exit 1
}

secret_value() {
  kubectl get secret "$2" \
    -o "jsonpath={.data.$3}" \
    --namespace "$1" \
    --context "${KUBE_CONTEXT}" \
    | base64 -d
}

ORIGIN="$(origin::public)" || fail "public origin unknown"

namespace::apply_ambient "${NAMESPACE}"

# Apply cert-manager Issuer and Certificate
kubectl apply \
  -f "$SCRIPT_DIR/trino-certificate.yaml" \
  --context "${KUBE_CONTEXT}"

# Apply the keystore password, KEDA secrets and TriggerAuthentication
kubectl apply \
  -f "$SCRIPT_DIR/secrets.yaml" \
  --context "${KUBE_CONTEXT}"

# Apply Prometheus RBAC so kube-prometheus can scrape Trino targets
kubectl apply \
  -f "$SCRIPT_DIR/prometheus-rolebinding.yaml" \
  --context "${KUBE_CONTEXT}"

# Wait for cert-manager to issue the CA + TLS certificates
kubectl wait \
  --for=condition=Ready certificate/trino-ca \
  --namespace "${NAMESPACE}" \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait \
  --for=condition=Ready certificate/trino-tls \
  --namespace "${NAMESPACE}" \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

# The internal shared secret is generated once: rotating it would split
# running coordinator and workers.
if [[ -z "$(kubectl get secret trino-internal-shared-secret \
  --ignore-not-found \
  -o name \
  --namespace "${NAMESPACE}" \
  --context "${KUBE_CONTEXT}")" ]]; then
  SHARED_SECRET="$(openssl rand -hex 32)"
  [[ -n "${SHARED_SECRET}" ]] || fail "openssl generated an empty shared secret"
  kubectl create secret generic trino-internal-shared-secret \
    --from-file=shared-secret=<(printf '%s' "${SHARED_SECRET}") \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" >/dev/null
  unset SHARED_SECRET
  echo "secret ${NAMESPACE}/trino-internal-shared-secret created"
fi

# trino-credentials is copied from its sources on every run, so a rotated
# Polaris, RustFS or Keycloak credential reaches Trino on the next bootstrap.
POLARIS_CREDENTIALS="$(secret_value lakehouse-catalog polaris-bootstrap-secret credentials)"
IFS=, read -r _realm POLARIS_CLIENT_ID POLARIS_CLIENT_SECRET <<<"${POLARIS_CREDENTIALS}" || true
unset POLARIS_CREDENTIALS
[[ -n "${POLARIS_CLIENT_ID:-}" ]] || fail "polaris-bootstrap-secret has an empty client id"
[[ -n "${POLARIS_CLIENT_SECRET:-}" ]] || fail "polaris-bootstrap-secret has an empty client secret"

EXCHANGE_S3_ACCESS_KEY="$(secret_value object-storage rustfs-secret RUSTFS_ACCESS_KEY)"
EXCHANGE_S3_SECRET_KEY="$(secret_value object-storage rustfs-secret RUSTFS_SECRET_KEY)"
[[ -n "${EXCHANGE_S3_ACCESS_KEY}" ]] || fail "rustfs-secret has an empty RUSTFS_ACCESS_KEY"
[[ -n "${EXCHANGE_S3_SECRET_KEY}" ]] || fail "rustfs-secret has an empty RUSTFS_SECRET_KEY"

OAUTH2_CLIENT_SECRET="$(secret_value identity keycloak-clients trino-client-secret)"
[[ -n "${OAUTH2_CLIENT_SECRET}" ]] || fail "keycloak-clients has an empty trino-client-secret"

kubectl create secret generic trino-credentials \
  --from-file=polaris-credential=<(printf '%s:%s' "${POLARIS_CLIENT_ID}" "${POLARIS_CLIENT_SECRET}") \
  --from-file=exchange-s3-access-key=<(printf '%s' "${EXCHANGE_S3_ACCESS_KEY}") \
  --from-file=exchange-s3-secret-key=<(printf '%s' "${EXCHANGE_S3_SECRET_KEY}") \
  --from-file=oauth2-client-secret=<(printf '%s' "${OAUTH2_CLIENT_SECRET}") \
  --dry-run=client \
  -o json \
  --namespace "${NAMESPACE}" \
  | jq '.metadata.labels = {
      "app.kubernetes.io/name": "trino",
      "app.kubernetes.io/instance": "trino",
      "app.kubernetes.io/component": "credentials",
      "app.kubernetes.io/part-of": "trino",
      "app.kubernetes.io/managed-by": "kubectl"
    }' \
  | kubectl apply --server-side \
    --field-manager trino-bootstrap \
    -f - \
    --context "${KUBE_CONTEXT}"
unset POLARIS_CLIENT_ID POLARIS_CLIENT_SECRET EXCHANGE_S3_ACCESS_KEY EXCHANGE_S3_SECRET_KEY \
  OAUTH2_CLIENT_SECRET

kubectl apply --server-side \
  --field-manager trino-bootstrap \
  -f - \
  --context "${KUBE_CONTEXT}" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: trino-public-origin
  namespace: ${NAMESPACE}
  labels:
    app.kubernetes.io/name: trino
    app.kubernetes.io/instance: trino
    app.kubernetes.io/component: config
    app.kubernetes.io/part-of: trino
    app.kubernetes.io/managed-by: kubectl
data:
  origin: ${ORIGIN}
EOF

# The pod templates carry a checksum of these Secrets and the origin
# ConfigMap (values.yaml, checksum/trino-env), so a changed value rolls the pods.
helm repo add trino https://trinodb.github.io/charts/
helm repo update trino

helm upgrade --install trino trino/trino \
  --version "${TRINO_VERSION}" \
  --namespace "${NAMESPACE}" \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
