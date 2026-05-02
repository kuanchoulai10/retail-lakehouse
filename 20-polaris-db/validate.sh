#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "PostgreSQL for Polaris is ready"
log::on_failure "PostgreSQL for Polaris is not ready"

kubectl rollout status deployment/polaris-db \
  --namespace polaris \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

POD=$(kubectl get pod \
  --selector app=polaris-db \
  --namespace polaris \
  --output jsonpath='{.items[0].metadata.name}' \
  --context "${KUBE_CONTEXT}")

kubectl exec "$POD" \
  --namespace polaris \
  --context "${KUBE_CONTEXT}" \
  -- pg_isready -U polaris -d polaris
