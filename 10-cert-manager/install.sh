#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Installing cert-manager v1.19.1 (context: ${KUBE_CONTEXT})"

helm upgrade --install cert-manager \
  oci://quay.io/jetstack/charts/cert-manager \
  --version v1.19.1 \
  --namespace cert-manager \
  --create-namespace \
  --values values.yaml \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
