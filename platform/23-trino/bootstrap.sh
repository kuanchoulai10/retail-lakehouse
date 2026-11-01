#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TRINO_VERSION="${TRINO_VERSION:-1.39.1}"
TIMEOUT="${TIMEOUT:-120s}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Trino ${TRINO_VERSION} installed"
log::on_failure "Trino installation failed"

namespace::apply_ambient lakehouse-query-engine

# Apply cert-manager Issuer and Certificate
kubectl apply \
  -f "$SCRIPT_DIR/trino-certificate.yaml" \
  --context "${KUBE_CONTEXT}"

# Apply KEDA secrets and TriggerAuthentication
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
  --namespace lakehouse-query-engine \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait \
  --for=condition=Ready certificate/trino-tls \
  --namespace lakehouse-query-engine \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

# Install Trino via Helm. Decrypt SOPS secrets into a variable first so a sops
# failure aborts under `set -e` (process substitution would silently feed helm
# an empty file). Then stream via process substitution to avoid a temp file
# whose EXIT trap would clash with log.sh.
helm repo add trino https://trinodb.github.io/charts/
helm repo update trino

SECRETS_YAML="$(sops -d "$SCRIPT_DIR/values-secret.yaml")"

helm upgrade --install trino trino/trino \
  --version "${TRINO_VERSION}" \
  --namespace lakehouse-query-engine \
  --values "$SCRIPT_DIR/values.yaml" \
  --values <(printf '%s' "$SECRETS_YAML") \
  --kube-context "${KUBE_CONTEXT}"
