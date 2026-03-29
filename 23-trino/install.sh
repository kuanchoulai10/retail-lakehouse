#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing Trino 1.39.1 (context: ${KUBE_CONTEXT})"

# Generate .env and values.yaml
bash generate-env.sh

# Load .env as environment variables
set -a
# shellcheck disable=SC1091
source ".env"
set +a

# Generate TLS certs and apply secret
bash generate-tls-certs.sh
kubectl apply -f ./trino-tls-secret.yaml -n trino --context "${KUBE_CONTEXT}"

# Generate and apply BigQuery secret
echo "==> Generating Kubernetes secret for BigQuery..."
# shellcheck disable=SC2154
kubectl create secret generic trino-bigquery-secret \
  --from-file=trino-sa.json="${GCP_SA_INPUT_PATH}" \
  --namespace trino \
  --dry-run=client -o yaml \
  | kubectl apply -f - --context "${KUBE_CONTEXT}"

# Install Trino via Helm
helm repo add trino https://trinodb.github.io/charts/
helm repo update trino

helm upgrade --install trino trino/trino \
  --version 1.39.1 \
  --namespace trino \
  --create-namespace \
  --values values.yaml \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
