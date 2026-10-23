#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
POLARIS_VERSION="${POLARIS_VERSION:-1.5.0}"
TIMEOUT="${TIMEOUT:-300s}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Apache Polaris ${POLARIS_VERSION} installed"
log::on_failure "Apache Polaris installation failed"

# Create namespace if not exists
kubectl create namespace lakehouse-catalog \
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
  --namespace lakehouse-catalog \
  --kube-context "${KUBE_CONTEXT}" >/dev/null 2>&1; then
  kubectl delete job polaris-bootstrap \
    --namespace lakehouse-catalog \
    --ignore-not-found \
    --context "${KUBE_CONTEXT}"
  kubectl apply \
    -f "$SCRIPT_DIR/polaris-bootstrap-job.yaml" \
    --context "${KUBE_CONTEXT}"
  kubectl wait \
    --for=condition=complete job/polaris-bootstrap \
    --namespace lakehouse-catalog \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
fi

# Install Polaris via wrapper Helm chart (vendored chart in charts/)
helm upgrade --install polaris "$SCRIPT_DIR" \
  --namespace lakehouse-catalog \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

# Wait for Polaris to be ready before creating the catalog
kubectl rollout status deployment/polaris \
  --namespace lakehouse-catalog \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

# Create the 'iceberg' catalog pointing to RustFS (idempotent: job skips if exists).
# validate.sh waits for the job to complete.
kubectl delete job polaris-create-catalog \
  --namespace lakehouse-catalog \
  --ignore-not-found \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/polaris-create-catalog-job.yaml" \
  --context "${KUBE_CONTEXT}"
