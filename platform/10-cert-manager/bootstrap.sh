#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
CERT_MANAGER_VERSION="${CERT_MANAGER_VERSION:-v1.19.1}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "cert-manager installed"
log::on_failure "cert-manager installation failed"

helm upgrade --install cert-manager \
  oci://quay.io/jetstack/charts/cert-manager \
  --version "${CERT_MANAGER_VERSION}" \
  --namespace cert-manager \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
