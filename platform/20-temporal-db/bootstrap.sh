#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "PostgreSQL for Temporal deployed"
log::on_failure "PostgreSQL for Temporal deployment failed"

namespace::apply_ambient temporal

kubectl apply \
  -f "$SCRIPT_DIR/temporal-db-secret.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/temporal-db-pvc.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/temporal-db-deployment.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/temporal-db-service.yaml" \
  --context "${KUBE_CONTEXT}"
