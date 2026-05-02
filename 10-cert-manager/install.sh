#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
CERT_MANAGER_VERSION="${CERT_MANAGER_VERSION:-v1.19.1}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing cert-manager ${CERT_MANAGER_VERSION} (context: ${KUBE_CONTEXT})"

helm upgrade --install cert-manager \
  oci://quay.io/jetstack/charts/cert-manager \
  --version "${CERT_MANAGER_VERSION}" \
  --namespace cert-manager \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
