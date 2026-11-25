#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
NAMESPACE="lakehouse-control-plane"
DB_USER="table_maintenance"

log::on_success "PostgreSQL for table maintenance deployed"
log::on_failure "PostgreSQL for table maintenance deployment failed"

fail() {
  echo "$1" >&2
  exit 1
}

namespace::apply_ambient "${NAMESPACE}"

EXISTING_DB_SECRET="$(kubectl get secret table-maintenance-db \
  --ignore-not-found \
  -o name \
  --namespace "${NAMESPACE}" \
  --context "${KUBE_CONTEXT}")"
if [[ -z "${EXISTING_DB_SECRET}" ]]; then
  DB_PASSWORD="$(openssl rand -hex 24)"
  [[ -n "${DB_PASSWORD}" ]] || fail "generated an empty database password"
  printf '%s' "${DB_PASSWORD}" \
    | kubectl create secret generic table-maintenance-db \
      --from-literal=username="${DB_USER}" \
      --from-file=password=/dev/stdin \
      --namespace "${NAMESPACE}" \
      --context "${KUBE_CONTEXT}" >/dev/null
  unset DB_PASSWORD
elif [[ -z "$(kubectl get secret table-maintenance-db \
  -o jsonpath='{.data.username}' \
  --namespace "${NAMESPACE}" \
  --context "${KUBE_CONTEXT}")" ]]; then
  kubectl patch secret table-maintenance-db \
    --type merge \
    --patch "{\"stringData\":{\"username\":\"${DB_USER}\"}}" \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" >/dev/null
fi

kubectl apply \
  -f "${SCRIPT_DIR}/table-maintenance-db-pvc.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "${SCRIPT_DIR}/table-maintenance-db-deployment.yaml" \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "${SCRIPT_DIR}/table-maintenance-db-service.yaml" \
  --context "${KUBE_CONTEXT}"
