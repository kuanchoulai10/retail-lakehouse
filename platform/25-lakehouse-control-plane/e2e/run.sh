#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel)"
source "${ROOT}/scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
E2E_MARKER="${1:-}"
NAMESPACE="lakehouse-control-plane"
START_TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-300}"
EXIT_TIMEOUT_SECONDS=60

case "${E2E_MARKER}" in
  critical) E2E_DEADLINE_SECONDS=1200 ;;
  full) E2E_DEADLINE_SECONDS=7200 ;;
  *)
    echo "usage: run.sh critical|full" >&2
    exit 2
    ;;
esac

BUILD_OUTPUT="$(KUBE_CONTEXT="${KUBE_CONTEXT}" bash "${SCRIPT_DIR}/../build.sh")"
E2E_TAG="$(sed -n 's/^E2E_TAG=//p' <<<"${BUILD_OUTPUT}")"
[[ -n "${E2E_TAG}" ]] || { echo "build.sh did not print E2E_TAG" >&2; exit 1; }
E2E_POD="table-maintenance-e2e-$(openssl rand -hex 4)"
export E2E_POD E2E_TAG E2E_MARKER E2E_DEADLINE_SECONDS

kube() {
  kubectl "$1" "${@:2}" --namespace "${NAMESPACE}" --context "${KUBE_CONTEXT}"
}

# shellcheck disable=SC2329
cleanup() {
  kube delete pod "${E2E_POD}" --ignore-not-found --wait=false >/dev/null 2>&1 || true
}
trap cleanup EXIT

pod_json() {
  kube get pod "${E2E_POD}" -o json
}

fail_with_events() {
  echo "$1" >&2
  kube get events --field-selector "involvedObject.name=${E2E_POD}" \
    -o custom-columns=TIME:.lastTimestamp,REASON:.reason,MESSAGE:.message >&2 || true
  kube logs "${E2E_POD}" --container principal >&2 2>/dev/null || true
  exit 1
}

# shellcheck disable=SC2016
envsubst '${E2E_POD} ${E2E_TAG} ${E2E_MARKER} ${E2E_DEADLINE_SECONDS}' <"${SCRIPT_DIR}/pod.yaml" \
  | kubectl apply -f - --context "${KUBE_CONTEXT}" >/dev/null
log::info "started ${E2E_POD} (table-maintenance-e2e:${E2E_TAG}, marker ${E2E_MARKER})"

STARTED=""
for ((waited = 0; waited < START_TIMEOUT_SECONDS; waited += 2)); do
  POD="$(pod_json)"
  STUCK="$(jq -r '[.status.initContainerStatuses[]?, .status.containerStatuses[]?
    | .state.waiting.reason // empty
    | select(test("ErrImage|ImagePull|InvalidImageName|CreateContainer"))] | first // empty' <<<"${POD}")"
  [[ -z "${STUCK}" ]] || fail_with_events "${E2E_POD} cannot start: ${STUCK}"
  PHASE="$(jq -r '.status.phase' <<<"${POD}")"
  [[ "${PHASE}" != "Failed" ]] || fail_with_events "${E2E_POD} failed before its scenarios ran"
  if jq -e '[.status.containerStatuses[]? | select(.name == "e2e")
      | .state.running or .state.terminated] | any' <<<"${POD}" >/dev/null; then
    STARTED=1
    break
  fi
  sleep 2
done
[[ -n "${STARTED}" ]] || fail_with_events "${E2E_POD} did not start its scenarios within ${START_TIMEOUT_SECONDS}s"

kube logs "${E2E_POD}" --container principal
kube logs "${E2E_POD}" --container e2e --follow

EXIT_CODE=""
for ((waited = 0; waited < EXIT_TIMEOUT_SECONDS; waited += 2)); do
  EXIT_CODE="$(pod_json | jq -r '.status.containerStatuses[]? | select(.name == "e2e")
    | .state.terminated.exitCode // empty')"
  [[ -z "${EXIT_CODE}" ]] || break
  sleep 2
done
[[ -n "${EXIT_CODE}" ]] || fail_with_events "${E2E_POD} has no exit code ${EXIT_TIMEOUT_SECONDS}s after its log ended"
if [[ "${EXIT_CODE}" == 0 ]]; then
  log::info "table maintenance e2e (${E2E_MARKER}) passed"
else
  echo "table maintenance e2e (${E2E_MARKER}) failed with exit code ${EXIT_CODE}" >&2
fi
exit "${EXIT_CODE}"
