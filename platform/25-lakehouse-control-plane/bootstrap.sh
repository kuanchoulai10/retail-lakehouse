#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-600s}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTROL_PLANE_NAMESPACE="lakehouse-control-plane"
OPERATIONS_NAMESPACE="lakehouse-maintenance-operations"
S3_REGION="$(yq '.catalog.s3Region' "${SCRIPT_DIR}/chart/values.yaml")"

log::on_success "Lakehouse control plane deployed"
log::on_failure "Lakehouse control plane deployment failed"

fail() {
  echo "$1" >&2
  exit 1
}

for namespace in "${CONTROL_PLANE_NAMESPACE}" "${OPERATIONS_NAMESPACE}"; do
  kubectl create namespace "${namespace}" \
    --dry-run=client \
    -o yaml \
    | kubectl apply \
      -f - \
      --context "${KUBE_CONTEXT}"
done

EXISTING_DB_SECRET="$(kubectl get secret table-maintenance-db \
  --ignore-not-found \
  -o name \
  --namespace "${CONTROL_PLANE_NAMESPACE}" \
  --context "${KUBE_CONTEXT}")"
if [[ -z "${EXISTING_DB_SECRET}" ]]; then
  DB_PASSWORD="$(openssl rand -hex 24)"
  [[ -n "${DB_PASSWORD}" ]] || fail "generated an empty database password"
  printf '%s' "${DB_PASSWORD}" \
    | kubectl create secret generic table-maintenance-db \
      --from-file=password=/dev/stdin \
      --namespace "${CONTROL_PLANE_NAMESPACE}" \
      --context "${KUBE_CONTEXT}" >/dev/null
  unset DB_PASSWORD
fi

POLARIS_CREDENTIALS="$(kubectl get secret polaris-bootstrap-secret \
  -o jsonpath='{.data.credentials}' \
  --namespace lakehouse-catalog \
  --context "${KUBE_CONTEXT}" \
  | base64 -d)"
IFS=, read -r _realm POLARIS_CLIENT_ID POLARIS_CLIENT_SECRET <<<"${POLARIS_CREDENTIALS}" || true
unset POLARIS_CREDENTIALS
[[ -n "${POLARIS_CLIENT_ID:-}" ]] \
  || fail "polaris-bootstrap-secret has an empty client id"
[[ -n "${POLARIS_CLIENT_SECRET:-}" ]] \
  || fail "polaris-bootstrap-secret has an empty client secret"

S3_ACCESS_KEY_ID="$(kubectl get secret rustfs-secret \
  -o jsonpath='{.data.RUSTFS_ACCESS_KEY}' \
  --namespace object-storage \
  --context "${KUBE_CONTEXT}" \
  | base64 -d)"
S3_SECRET_ACCESS_KEY="$(kubectl get secret rustfs-secret \
  -o jsonpath='{.data.RUSTFS_SECRET_KEY}' \
  --namespace object-storage \
  --context "${KUBE_CONTEXT}" \
  | base64 -d)"
[[ -n "${S3_ACCESS_KEY_ID}" ]] || fail "rustfs-secret has an empty RUSTFS_ACCESS_KEY"
[[ -n "${S3_SECRET_ACCESS_KEY}" ]] || fail "rustfs-secret has an empty RUSTFS_SECRET_KEY"
[[ -n "${S3_REGION}" && "${S3_REGION}" != "null" ]] \
  || fail "chart values have no catalog.s3Region"
for value in "${POLARIS_CLIENT_ID}" "${POLARIS_CLIENT_SECRET}" \
  "${S3_ACCESS_KEY_ID}" "${S3_SECRET_ACCESS_KEY}"; do
  [[ "${value}" != *[\"\\]* ]] || fail "a credential contains a quote or a backslash"
done

for namespace in "${CONTROL_PLANE_NAMESPACE}" "${OPERATIONS_NAMESPACE}"; do
  printf 'apiVersion: v1\nkind: Secret\nmetadata:\n  name: %s\n  namespace: %s\nstringData:\n  credential: "%s:%s"\n' \
    table-maintenance-polaris-credential "${namespace}" \
    "${POLARIS_CLIENT_ID}" "${POLARIS_CLIENT_SECRET}" \
    | kubectl apply \
      -f - \
      --context "${KUBE_CONTEXT}" >/dev/null

  printf 'apiVersion: v1\nkind: Secret\nmetadata:\n  name: %s\n  namespace: %s\nstringData:\n  AWS_ACCESS_KEY_ID: "%s"\n  AWS_SECRET_ACCESS_KEY: "%s"\n  AWS_REGION: "%s"\n' \
    table-maintenance-s3 "${namespace}" \
    "${S3_ACCESS_KEY_ID}" "${S3_SECRET_ACCESS_KEY}" "${S3_REGION}" \
    | kubectl apply \
      -f - \
      --context "${KUBE_CONTEXT}" >/dev/null
done
unset POLARIS_CLIENT_ID POLARIS_CLIENT_SECRET S3_ACCESS_KEY_ID S3_SECRET_ACCESS_KEY

BUILD_OUTPUT="$(KUBE_CONTEXT="${KUBE_CONTEXT}" bash "${SCRIPT_DIR}/build.sh")"
BACKEND_TAG="$(sed -n 's/^BACKEND_TAG=//p' <<<"${BUILD_OUTPUT}")"
SPARK_TAG="$(sed -n 's/^SPARK_TAG=//p' <<<"${BUILD_OUTPUT}")"
[[ -n "${BACKEND_TAG}" && -n "${SPARK_TAG}" ]] || fail "build.sh did not print image tags"

helm upgrade --install table-maintenance "${SCRIPT_DIR}/chart" \
  --namespace "${CONTROL_PLANE_NAMESPACE}" \
  --set image.backend.tag="${BACKEND_TAG}" \
  --set image.spark.tag="${SPARK_TAG}" \
  --wait \
  --wait-for-jobs \
  --timeout "${TIMEOUT}" \
  --kube-context "${KUBE_CONTEXT}"
