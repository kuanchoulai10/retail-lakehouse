#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
POLARIS_VERSION="${POLARIS_VERSION:-1.3.0-incubating}"
TIMEOUT="${TIMEOUT:-300s}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Apache Polaris ${POLARIS_VERSION} installed"
log::on_failure "Apache Polaris installation failed"

# Create namespace if not exists
kubectl create namespace polaris \
  --dry-run=client \
  -o yaml \
  | kubectl apply \
    -f - \
    --context "${KUBE_CONTEXT}"

kubectl apply \
  -f "$SCRIPT_DIR/polaris-storage-secret.yaml" \
  --context "${KUBE_CONTEXT}"

kubectl apply \
  -f "$SCRIPT_DIR/polaris-bootstrap-secret.yaml" \
  --context "${KUBE_CONTEXT}"

# Bootstrap Polaris schema in PostgreSQL on first install only.
# Skip if the Helm release already exists (schema is persisted in polaris-db).
if ! helm status polaris \
  --namespace polaris \
  --kube-context "${KUBE_CONTEXT}" >/dev/null 2>&1; then
  kubectl delete job polaris-bootstrap \
    --namespace polaris \
    --ignore-not-found \
    --context "${KUBE_CONTEXT}"
  kubectl apply \
    -f "$SCRIPT_DIR/polaris-bootstrap-job.yaml" \
    --context "${KUBE_CONTEXT}"
  kubectl wait \
    --for=condition=complete job/polaris-bootstrap \
    --namespace polaris \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
fi

# Install Polaris via wrapper Helm chart (vendored chart in charts/)
helm upgrade --install polaris "$SCRIPT_DIR" \
  --namespace polaris \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

# Wait for Polaris to be ready before creating the catalog
kubectl rollout status deployment/polaris \
  --namespace polaris \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

# Create the 'iceberg' catalog pointing to MinIO (idempotent: job skips if exists).
# validate.sh waits for the job to complete.
kubectl delete job polaris-create-catalog \
  --namespace polaris \
  --ignore-not-found \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/polaris-create-catalog-job.yaml" \
  --context "${KUBE_CONTEXT}"
