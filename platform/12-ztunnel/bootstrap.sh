#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.8}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "ztunnel installed"
log::on_failure "ztunnel installation failed"

helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update istio

helm upgrade --install ztunnel istio/ztunnel \
  --version "${ISTIO_VERSION}" \
  --namespace istio-system \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
