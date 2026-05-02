#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying PostgreSQL for Polaris (context: ${KUBE_CONTEXT})"

# Create namespace if not exists (idempotent)
kubectl create namespace polaris --dry-run=client -o yaml \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

# Apply in order: Secret first (Deployment depends on it via secretKeyRef)
kubectl apply -f "$SCRIPT_DIR/polaris-db-secret.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/polaris-db-pvc.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/polaris-db-deployment.yaml" --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/polaris-db-service.yaml" --context "${KUBE_CONTEXT}"

echo "==> Done."
