#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
POLARIS_VERSION="${POLARIS_VERSION:-1.3.0-incubating}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Apache Polaris ${POLARIS_VERSION} (context: ${KUBE_CONTEXT})"

# Create namespace if not exists
kubectl create namespace polaris --dry-run=client -o yaml \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

kubectl apply -f "$SCRIPT_DIR/polaris-storage-secret.yaml" --context "${KUBE_CONTEXT}"

kubectl apply -f "$SCRIPT_DIR/polaris-bootstrap-secret.yaml" --context "${KUBE_CONTEXT}"

# Bootstrap Polaris schema in PostgreSQL on first install only.
# Skip if the Helm release already exists (schema is persisted in polaris-db).
if helm status polaris -n polaris --kube-context "${KUBE_CONTEXT}" >/dev/null 2>&1; then
  echo "==> Polaris release exists, skipping schema bootstrap"
else
  echo "==> Bootstrapping Polaris schema in polaris-db..."
  kubectl --context "${KUBE_CONTEXT}" delete job polaris-bootstrap -n polaris --ignore-not-found
  kubectl apply -f "$SCRIPT_DIR/polaris-bootstrap-job.yaml" --context "${KUBE_CONTEXT}"
  kubectl --context "${KUBE_CONTEXT}" wait --for=condition=complete job/polaris-bootstrap \
    -n polaris --timeout=120s
fi

# Install Polaris via wrapper Helm chart (vendored chart in charts/)
helm upgrade --install polaris \
  "$SCRIPT_DIR" \
  --namespace polaris \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

# Wait for Polaris to be ready before creating the catalog
kubectl --context "${KUBE_CONTEXT}" rollout status deployment/polaris \
  -n polaris --timeout=300s

# Create the 'iceberg' catalog pointing to MinIO (idempotent: job skips if exists)
echo "==> Ensuring 'iceberg' catalog is registered in Polaris..."
kubectl --context "${KUBE_CONTEXT}" delete job polaris-create-catalog -n polaris --ignore-not-found
kubectl apply -f "$SCRIPT_DIR/polaris-create-catalog-job.yaml" --context "${KUBE_CONTEXT}"
kubectl --context "${KUBE_CONTEXT}" wait --for=condition=complete job/polaris-create-catalog \
  -n polaris --timeout=120s

echo "==> Done."
