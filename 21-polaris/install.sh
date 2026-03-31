#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
POLARIS_VERSION="${POLARIS_VERSION:-1.3.0-incubating}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Apache Polaris ${POLARIS_VERSION} (context: ${KUBE_CONTEXT})"

# Create namespace if not exists
kubectl create namespace polaris --dry-run=client -o yaml \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

# Apply SOPS-encrypted secrets
sops --decrypt "$SCRIPT_DIR/polaris-storage-secret.yaml" \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

sops --decrypt "$SCRIPT_DIR/polaris-bootstrap-secret.yaml" \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

# Install Polaris via wrapper Helm chart (vendored chart in charts/)
helm upgrade --install polaris \
  "$SCRIPT_DIR" \
  --namespace polaris \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
