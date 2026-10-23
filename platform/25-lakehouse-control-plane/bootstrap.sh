#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-600s}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTROL_PLANE_NAMESPACE="lakehouse-control-plane"
OPERATIONS_NAMESPACE="lakehouse-maintenance-operations"
S3_REGION="dummy-region"

log::on_success "Lakehouse control plane deployed"
log::on_failure "Lakehouse control plane deployment failed"

for namespace in "${CONTROL_PLANE_NAMESPACE}" "${OPERATIONS_NAMESPACE}"; do
  kubectl create namespace "${namespace}" \
    --dry-run=client \
    -o yaml \
    | kubectl apply \
      -f - \
      --context "${KUBE_CONTEXT}"
done

DB_SECRET_READY="$(kubectl get secret table-maintenance-db \
  -o go-template='{{if index .data "password"}}ok{{end}}' \
  --namespace "${CONTROL_PLANE_NAMESPACE}" \
  --context "${KUBE_CONTEXT}" 2>/dev/null || true)"
if [[ "${DB_SECRET_READY}" != "ok" ]]; then
  kubectl create secret generic table-maintenance-db \
    --from-file=password=<(openssl rand -hex 24 | tr -d '\n') \
    --dry-run=client \
    -o yaml \
    --namespace "${CONTROL_PLANE_NAMESPACE}" \
    | kubectl apply \
      -f - \
      --context "${KUBE_CONTEXT}"
fi

for namespace in "${CONTROL_PLANE_NAMESPACE}" "${OPERATIONS_NAMESPACE}"; do
  kubectl get secret polaris-bootstrap-secret \
    -o jsonpath='{.data.credentials}' \
    --namespace lakehouse-catalog \
    --context "${KUBE_CONTEXT}" \
    | base64 -d \
    | awk -F, '{printf "%s:%s", $2, $3}' \
    | kubectl create secret generic table-maintenance-polaris-credential \
      --from-file=credential=/dev/stdin \
      --dry-run=client \
      -o yaml \
      --namespace "${namespace}" \
    | kubectl apply \
      -f - \
      --context "${KUBE_CONTEXT}"

  kubectl create secret generic table-maintenance-s3 \
    --from-file=AWS_ACCESS_KEY_ID=<(kubectl get secret rustfs-secret \
      -o jsonpath='{.data.RUSTFS_ACCESS_KEY}' \
      --namespace object-storage \
      --context "${KUBE_CONTEXT}" | base64 -d) \
    --from-file=AWS_SECRET_ACCESS_KEY=<(kubectl get secret rustfs-secret \
      -o jsonpath='{.data.RUSTFS_SECRET_KEY}' \
      --namespace object-storage \
      --context "${KUBE_CONTEXT}" | base64 -d) \
    --from-file=AWS_REGION=<(printf '%s' "${S3_REGION}") \
    --dry-run=client \
    -o yaml \
    --namespace "${namespace}" \
    | kubectl apply \
      -f - \
      --context "${KUBE_CONTEXT}"
done

BUILD_OUTPUT="$(KUBE_CONTEXT="${KUBE_CONTEXT}" bash "${SCRIPT_DIR}/build.sh")"
BACKEND_TAG="$(sed -n 's/^BACKEND_TAG=//p' <<<"${BUILD_OUTPUT}")"
SPARK_TAG="$(sed -n 's/^SPARK_TAG=//p' <<<"${BUILD_OUTPUT}")"

helm upgrade --install table-maintenance "${SCRIPT_DIR}/chart" \
  --namespace "${CONTROL_PLANE_NAMESPACE}" \
  --set image.backend.tag="${BACKEND_TAG}" \
  --set image.spark.tag="${SPARK_TAG}" \
  --wait \
  --timeout "${TIMEOUT}" \
  --kube-context "${KUBE_CONTEXT}"
