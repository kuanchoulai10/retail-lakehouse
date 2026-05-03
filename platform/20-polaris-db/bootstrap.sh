#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "PostgreSQL for Polaris deployed"
log::on_failure "PostgreSQL for Polaris deployment failed"

# Create namespace if not exists (idempotent)
kubectl create namespace polaris \
  --dry-run=client \
  -o yaml \
  | kubectl apply \
    -f - \
    --context "${KUBE_CONTEXT}"

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
