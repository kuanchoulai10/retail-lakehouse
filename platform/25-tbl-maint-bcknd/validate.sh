#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Backend is ready"
log::on_failure "Backend is not ready"

kubectl rollout status deployment/table-maintenance-backend \
  --namespace default \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

POD=$(kubectl get pod \
  --selector app=table-maintenance-backend \
  --namespace default \
  --output jsonpath='{.items[0].metadata.name}' \
  --context "${KUBE_CONTEXT}")

kubectl exec "$POD" \
  --namespace default \
  --context "${KUBE_CONTEXT}" \
  -- python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
