#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
POLARIS_VERSION="${POLARIS_VERSION:-1.3.0-incubating}"
POLARIS_BOOTSTRAP_CREDENTIALS="${POLARIS_BOOTSTRAP_CREDENTIALS:-POLARIS,root,secret}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Apache Polaris ${POLARIS_VERSION} (context: ${KUBE_CONTEXT})"

# Create namespace if not exists
kubectl create namespace polaris --dry-run=client -o yaml \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

# Create MinIO storage credentials secret
kubectl create secret generic polaris-storage-secret \
  --from-literal=awsAccessKeyId=minio_user \
  --from-literal=awsSecretAccessKey=minio_password \
  --namespace polaris \
  --dry-run=client -o yaml \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

# Create bootstrap credentials secret (realm,username,password)
kubectl create secret generic polaris-bootstrap-secret \
  --from-literal=credentials="${POLARIS_BOOTSTRAP_CREDENTIALS}" \
  --namespace polaris \
  --dry-run=client -o yaml \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

# Install Polaris via Helm
helm upgrade --install polaris \
  "https://downloads.apache.org/incubator/polaris/helm-chart/1.3.0-incubating/polaris-1.3.0-incubating.tgz" \
  --namespace polaris \
  --values "$SCRIPT_DIR/values.yaml" \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
