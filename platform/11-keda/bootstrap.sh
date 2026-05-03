#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
KEDA_VERSION="${KEDA_VERSION:-2.18.0}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "KEDA installed"
log::on_failure "KEDA installation failed"

helm repo add kedacore https://kedacore.github.io/charts
helm repo update kedacore

helm upgrade --install keda kedacore/keda \
  --version "${KEDA_VERSION}" \
  --namespace keda \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
