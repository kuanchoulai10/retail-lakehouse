#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/gateway.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-600s}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS_PROFILE="${SETTINGS_PROFILE:-default}"
case "${SETTINGS_PROFILE}" in
  default) PROFILE_VALUES=() ;;
  e2e) PROFILE_VALUES=(--values "${SCRIPT_DIR}/values/e2e.yaml") ;;
  *) echo "SETTINGS_PROFILE must be default or e2e, not ${SETTINGS_PROFILE}" >&2; exit 1 ;;
esac

CONTROL_PLANE_NAMESPACE="lakehouse-control-plane"
OPERATIONS_NAMESPACE="lakehouse-maintenance-operations"
S3_REGION="$(yq '.external.objectStorage.s3.region' "${SCRIPT_DIR}/values/minikube.yaml")"
[[ -n "${S3_REGION}" && "${S3_REGION}" != "null" ]] \
  || { echo "values/minikube.yaml names no S3 region" >&2; exit 1; }

log::on_success "Lakehouse control plane deployed (settings profile: ${SETTINGS_PROFILE})"
log::on_failure "Lakehouse control plane deployment failed"

fail() {
  echo "$1" >&2
  exit 1
}

upsert_secret() {
  local name="$1"
  local namespace="$2"
  local manifest
  manifest="$(cat)"
  local existing
  existing="$(kubectl get secret "${name}" \
    --ignore-not-found \
    -o name \
    --namespace "${namespace}" \
    --context "${KUBE_CONTEXT}")"
  if [[ -z "${existing}" ]]; then
    kubectl create \
      -f - \
      --context "${KUBE_CONTEXT}" >/dev/null <<<"${manifest}"
  else
    kubectl apply --server-side --force-conflicts \
      --field-manager table-maintenance-bootstrap \
      -f - \
      --context "${KUBE_CONTEXT}" >/dev/null <<<"${manifest}"
  fi
}

for namespace in "${CONTROL_PLANE_NAMESPACE}" "${OPERATIONS_NAMESPACE}"; do
  namespace::apply_ambient "${namespace}"
done
gateway::allow_routes "${CONTROL_PLANE_NAMESPACE}"

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
for value in "${POLARIS_CLIENT_ID}" "${POLARIS_CLIENT_SECRET}" \
  "${S3_ACCESS_KEY_ID}" "${S3_SECRET_ACCESS_KEY}"; do
  [[ "${value}" != *[\"\\]* ]] || fail "a credential contains a quote or a backslash"
done

for namespace in "${CONTROL_PLANE_NAMESPACE}" "${OPERATIONS_NAMESPACE}"; do
  printf 'apiVersion: v1\nkind: Secret\nmetadata:\n  name: %s\n  namespace: %s\nstringData:\n  credential: "%s:%s"\n' \
    table-maintenance-polaris-credential "${namespace}" \
    "${POLARIS_CLIENT_ID}" "${POLARIS_CLIENT_SECRET}" \
    | upsert_secret table-maintenance-polaris-credential "${namespace}"

  printf 'apiVersion: v1\nkind: Secret\nmetadata:\n  name: %s\n  namespace: %s\nstringData:\n  AWS_ACCESS_KEY_ID: "%s"\n  AWS_SECRET_ACCESS_KEY: "%s"\n  AWS_REGION: "%s"\n' \
    table-maintenance-s3 "${namespace}" \
    "${S3_ACCESS_KEY_ID}" "${S3_SECRET_ACCESS_KEY}" "${S3_REGION}" \
    | upsert_secret table-maintenance-s3 "${namespace}"
done
unset POLARIS_CLIENT_ID POLARIS_CLIENT_SECRET S3_ACCESS_KEY_ID S3_SECRET_ACCESS_KEY

BUILD_OUTPUT="$(KUBE_CONTEXT="${KUBE_CONTEXT}" bash "${SCRIPT_DIR}/build.sh")"
BACKEND_TAG="$(sed -n 's/^BACKEND_TAG=//p' <<<"${BUILD_OUTPUT}")"
SPARK_TAG="$(sed -n 's/^SPARK_TAG=//p' <<<"${BUILD_OUTPUT}")"
CONSOLE_TAG="$(sed -n 's/^CONSOLE_TAG=//p' <<<"${BUILD_OUTPUT}")"
[[ -n "${BACKEND_TAG}" && -n "${SPARK_TAG}" && -n "${CONSOLE_TAG}" ]] \
  || fail "build.sh did not print image tags"

helm upgrade --install table-maintenance "${SCRIPT_DIR}/chart" \
  --namespace "${CONTROL_PLANE_NAMESPACE}" \
  --values "${SCRIPT_DIR}/values/minikube.yaml" \
  ${PROFILE_VALUES[@]+"${PROFILE_VALUES[@]}"} \
  --set-string backend.image.tag="${BACKEND_TAG}" \
  --set-string maintenance.jobs.image.tag="${SPARK_TAG}" \
  --set-string frontend.image.tag="${CONSOLE_TAG}" \
  --wait \
  --wait-for-jobs \
  --timeout "${TIMEOUT}" \
  --kube-context "${KUBE_CONTEXT}"
