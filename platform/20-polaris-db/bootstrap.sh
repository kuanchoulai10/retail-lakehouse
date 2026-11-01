#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "PostgreSQL for Polaris deployed"
log::on_failure "PostgreSQL for Polaris deployment failed"

namespace::apply_ambient lakehouse-catalog

# Apply in order: Secret first (Deployment depends on it via secretKeyRef)
kubectl apply \
  -f "$SCRIPT_DIR/polaris-db-secret.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/polaris-db-pvc.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/polaris-db-deployment.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/polaris-db-service.yaml" \
  --context "${KUBE_CONTEXT}"
