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
GRACE_SECONDS=900

case "${E2E_MARKER}" in
  critical)
    E2E_MARKERS="critical"
    E2E_DEADLINE_SECONDS=1200
    ;;
  full)
    E2E_MARKERS="critical or full"
    E2E_DEADLINE_SECONDS=7200
    ;;
  *)
    echo "usage: run.sh critical|full" >&2
    exit 2
    ;;
esac

BUILD_OUTPUT="$(KUBE_CONTEXT="${KUBE_CONTEXT}" bash "${SCRIPT_DIR}/../build.sh")"
E2E_TAG="$(sed -n 's/^E2E_TAG=//p' <<<"${BUILD_OUTPUT}")"
[[ -n "${E2E_TAG}" ]] || { echo "build.sh did not print E2E_TAG" >&2; exit 1; }
E2E_POD="table-maintenance-e2e-$(openssl rand -hex 4)"
export E2E_POD E2E_TAG E2E_MARKERS E2E_DEADLINE_SECONDS

kube() {
  kubectl "$1" "${@:2}" --namespace "${NAMESPACE}" --context "${KUBE_CONTEXT}"
}

HOLDER_SELECTOR="app.kubernetes.io/name=table-maintenance-e2e,app.kubernetes.io/component=queue-holder"
OURS=""

# A queue holder outlives a pod that is killed outright and holds the normal queue until it is
# deleted; once this run is the only one, every holder is its own.
# shellcheck disable=SC2329
cleanup() {
  kube delete pod "${E2E_POD}" --ignore-not-found --wait=false >/dev/null 2>&1 || true
  if [[ -n "${OURS}" ]]; then
    kubectl delete podgroups --namespace lakehouse-maintenance-operations --context "${KUBE_CONTEXT}" \
      --selector "${HOLDER_SELECTOR}" --ignore-not-found --wait=false >/dev/null 2>&1 || true
  fi
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

ACTIVE="$(kubectl get pods --selector app.kubernetes.io/name=table-maintenance-e2e --output json \
  --namespace "${NAMESPACE}" --context "${KUBE_CONTEXT}" | jq -r '[.items[]
  | select(.status.phase == "Pending" or .status.phase == "Running") | .metadata.name] | join(" ")')"
if [[ -n "${ACTIVE}" ]]; then
  echo "another e2e run is still going on ${KUBE_CONTEXT} (${ACTIVE}): runs share the tm-e2e principal" \
    "and each run removes the names an earlier one left, so wait until it ends" >&2
  trap - EXIT
  exit 1
fi
OURS=1

kubectl apply -f "${SCRIPT_DIR}/rbac.yaml" --context "${KUBE_CONTEXT}" >/dev/null
# shellcheck disable=SC2016
envsubst '${E2E_POD} ${E2E_TAG} ${E2E_MARKERS} ${E2E_DEADLINE_SECONDS}' <"${SCRIPT_DIR}/pod.yaml" \
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

e2e_state() {
  local pod
  pod="$(pod_json 2>/dev/null)" || { echo gone; return; }
  jq -r '.status.containerStatuses[]? | select(.name == "e2e")
    | if .state.terminated then "terminated" else "running" end' <<<"${pod}"
}

kube logs "${E2E_POD}" --container principal
FOLLOW_UNTIL=$((SECONDS + E2E_DEADLINE_SECONDS + GRACE_SECONDS))
SINCE=""
while :; do
  kube logs "${E2E_POD}" --container e2e --follow ${SINCE:+--since-time "${SINCE}"} || true
  STATE="$(e2e_state)"
  [[ "${STATE}" != "gone" ]] || fail_with_events "${E2E_POD} was deleted before its scenarios ended"
  [[ "${STATE}" != "terminated" ]] || break
  ((SECONDS < FOLLOW_UNTIL)) || fail_with_events "${E2E_POD} still runs past its deadline and grace period"
  SINCE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  log::info "the log of ${E2E_POD} ended while its scenarios still run; following it again"
  sleep 2
done

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
