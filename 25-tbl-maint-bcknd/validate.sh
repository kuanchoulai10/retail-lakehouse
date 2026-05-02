#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::header "Validating table-maintenance backend"

kubectl rollout status deployment/table-maintenance-backend \
  -n default --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

log::step "Checking health endpoint"
kubectl exec -n default \
  "$(kubectl get pod -l app=table-maintenance-backend -n default --context "${KUBE_CONTEXT}" -o jsonpath='{.items[0].metadata.name}')" \
  --context "${KUBE_CONTEXT}" \
  -- python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"

log::footer "Backend is ready"
