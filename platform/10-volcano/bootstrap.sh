#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
VOLCANO_VERSION="${VOLCANO_VERSION:-1.16.0}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Volcano installed"
log::on_failure "Volcano installation failed"

helm repo add volcano-sh https://volcano-sh.github.io/helm-charts
helm repo update volcano-sh

helm upgrade --install volcano volcano-sh/volcano \
  --version "${VOLCANO_VERSION}" \
  --namespace volcano-system \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
