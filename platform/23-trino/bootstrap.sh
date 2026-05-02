#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TRINO_VERSION="${TRINO_VERSION:-1.39.1}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Trino ${TRINO_VERSION} (context: ${KUBE_CONTEXT})"

# Create namespace if not exists
kubectl create namespace trino --dry-run=client -o yaml \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

# Apply cert-manager Issuer and Certificate
kubectl apply -f "$SCRIPT_DIR/trino-certificate.yaml" --context "${KUBE_CONTEXT}"

# Apply KEDA secrets and TriggerAuthentication
kubectl apply -f "$SCRIPT_DIR/secrets.yaml" --context "${KUBE_CONTEXT}"

# Apply Prometheus RBAC so kube-prometheus can scrape Trino targets
kubectl apply -f "$SCRIPT_DIR/prometheus-rolebinding.yaml" --context "${KUBE_CONTEXT}"

# Wait for cert-manager to issue the CA + TLS certificates
echo "==> Waiting for cert-manager to issue CA certificate..."
kubectl wait --for=condition=Ready certificate/trino-ca \
  -n trino --timeout=120s --context "${KUBE_CONTEXT}"

echo "==> Waiting for cert-manager to issue TLS certificate..."
kubectl wait --for=condition=Ready certificate/trino-tls \
  -n trino --timeout=120s --context "${KUBE_CONTEXT}"

# Install Trino via Helm
helm repo add trino https://trinodb.github.io/charts/
helm repo update trino

# Decrypt SOPS-encrypted values to a temp file
SECRETS_TMP="$(mktemp /tmp/trino-values-secret-XXXXXX.yaml)"
trap 'rm -f "$SECRETS_TMP"' EXIT
sops -d "$SCRIPT_DIR/values-secret.yaml" > "$SECRETS_TMP"

helm upgrade --install trino trino/trino \
  --version "${TRINO_VERSION}" \
  --namespace trino \
  --values "$SCRIPT_DIR/values.yaml" \
  --values "$SECRETS_TMP" \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
