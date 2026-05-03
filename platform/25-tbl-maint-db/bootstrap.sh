#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "PostgreSQL for table-maintenance deployed"
log::on_failure "PostgreSQL for table-maintenance deployment failed"

kubectl apply \
  -f "$SCRIPT_DIR/postgres-pvc.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/postgres-deployment.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/postgres-service.yaml" \
  --context "${KUBE_CONTEXT}"
