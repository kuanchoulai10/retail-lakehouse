#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
ISTIO_VERSION="${ISTIO_VERSION:-1.26.2}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "istio-ingressgateway installed"
log::on_failure "istio-ingressgateway installation failed"

helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update istio

helm upgrade --install istio-ingressgateway istio/gateway \
  --version "${ISTIO_VERSION}" \
  --namespace istio-ingress \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
