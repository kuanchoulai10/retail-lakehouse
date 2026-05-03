#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
STRIMZI_VERSION="${STRIMZI_VERSION:-0.46.1}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Strimzi Operator installed"
log::on_failure "Strimzi Operator installation failed"

helm repo add strimzi https://strimzi.io/charts/
helm repo update strimzi

helm upgrade --install strimzi-operator strimzi/strimzi-kafka-operator \
  --version "${STRIMZI_VERSION}" \
  --namespace strimzi-operator \
  --create-namespace \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"
