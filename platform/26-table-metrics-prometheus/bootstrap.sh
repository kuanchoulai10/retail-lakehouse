#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Table metrics Prometheus deployed"
log::on_failure "Table metrics Prometheus deployment failed"

namespace::apply_ambient table-metrics

kubectl apply \
  -f "$SCRIPT_DIR/prometheus-configmap.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/prometheus-pvc.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/prometheus-deployment.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/prometheus-service.yaml" \
  --context "${KUBE_CONTEXT}"
