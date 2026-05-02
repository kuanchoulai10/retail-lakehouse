#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::quiet "PostgreSQL for Polaris is ready"

kubectl wait pod \
  -l app=polaris-db \
  -n polaris \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

log::step "Verifying PostgreSQL is accepting connections"
POD=$(kubectl get pod -l app=polaris-db -n polaris \
  --context "${KUBE_CONTEXT}" -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n polaris "$POD" --context "${KUBE_CONTEXT}" \
  -- pg_isready -U polaris -d polaris