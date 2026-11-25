#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"
NAMESPACE="lakehouse-control-plane"

log::on_success "PostgreSQL for table maintenance is ready"
log::on_failure "PostgreSQL for table maintenance is not ready"

namespace::assert_ambient "${NAMESPACE}"

for key in username password; do
  [[ -n "$(kubectl get secret table-maintenance-db \
    -o jsonpath="{.data.${key}}" \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}")" ]] \
    || { echo "Secret table-maintenance-db has no ${key}" >&2; exit 1; }
done

kubectl rollout status deployment/table-maintenance-db \
  --namespace "${NAMESPACE}" \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

POD=$(kubectl get pod \
  --selector app.kubernetes.io/name=postgres,app.kubernetes.io/instance=table-maintenance-db \
  --namespace "${NAMESPACE}" \
  --output jsonpath='{.items[0].metadata.name}' \
  --context "${KUBE_CONTEXT}")

kubectl exec "${POD}" \
  --namespace "${NAMESPACE}" \
  --context "${KUBE_CONTEXT}" \
  -- pg_isready -U table_maintenance -d table_maintenance
