#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TEMPORAL_CHART_VERSION="${TEMPORAL_CHART_VERSION:-1.7.0}"
TIMEOUT="${TIMEOUT:-600s}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Temporal chart ${TEMPORAL_CHART_VERSION} installed"
log::on_failure "Temporal installation failed"

helm repo add temporalio https://go.temporal.io/helm-charts --force-update
helm repo update temporalio

kubectl create namespace temporal \
  --dry-run=client \
  -o yaml \
  | kubectl apply \
    -f - \
    --context "${KUBE_CONTEXT}"

helm upgrade --install temporal temporalio/temporal \
  --version "${TEMPORAL_CHART_VERSION}" \
  --namespace temporal \
  --values "$SCRIPT_DIR/values.yaml" \
  --timeout "${TIMEOUT}" \
  --kube-context "${KUBE_CONTEXT}"
