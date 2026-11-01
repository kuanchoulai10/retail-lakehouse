#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
KIALI_VERSION="${KIALI_VERSION:-2.20.0}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Kiali installed"
log::on_failure "Kiali installation failed"

helm repo add kiali https://kiali.org/helm-charts
helm repo update kiali

helm upgrade --install kiali-server kiali/kiali-server \
  --version "${KIALI_VERSION}" \
  --namespace istio-system \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

kubectl apply \
  -f "$SCRIPT_DIR/../22-polaris-routes/gateway.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/kiali-route.yaml" \
  --context "${KUBE_CONTEXT}"
