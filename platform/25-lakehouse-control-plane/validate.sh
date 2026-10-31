#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"
NAMESPACE="lakehouse-control-plane"
GATEWAY_PORT="${GATEWAY_PORT:-18080}"
GATEWAY_PID=""

log::on_success "Lakehouse control plane is ready"
log::on_failure "Lakehouse control plane is not ready"

cleanup() {
  if [[ -n "${GATEWAY_PID}" ]]; then
    kill "${GATEWAY_PID}" 2>/dev/null || true
  fi
}
trap '__log::on_exit $?; cleanup' EXIT

for namespace in "${NAMESPACE}" lakehouse-maintenance-operations; do
  kubectl wait "namespace/${namespace}" \
    --for jsonpath='{.status.phase}'=Active \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
done

for deployment in table-maintenance-db table-maintenance-api table-maintenance-worker \
  table-maintenance-event-consumer console; do
  kubectl rollout status "deployment/${deployment}" \
    --namespace "${NAMESPACE}" \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
done

RELEASE_REVISION="$(helm status table-maintenance \
  --namespace "${NAMESPACE}" \
  --kube-context "${KUBE_CONTEXT}" \
  -o json \
  | yq '.version')"
kubectl wait "job/table-maintenance-migrate-${RELEASE_REVISION}" \
  --for=condition=complete \
  --timeout "${TIMEOUT}" \
  --namespace "${NAMESPACE}" \
  --context "${KUBE_CONTEXT}"

CATALOGS="$(kubectl get configmap table-maintenance-config \
  -o jsonpath='{.data.GLAC_CATALOG__NAMES}' \
  --namespace "${NAMESPACE}" \
  --context "${KUBE_CONTEXT}" \
  | yq '.[]')"
[[ -n "${CATALOGS}" ]] || { echo "no catalogs configured" >&2; exit 1; }

api_get() {
  kubectl exec deployment/table-maintenance-api \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" \
    -- python -c "import sys, urllib.request; r = urllib.request.urlopen('http://localhost:8000' + sys.argv[1], timeout=10); print(sys.argv[1], r.status)" "$1"
}

api_get /healthz
api_get /v1/table-discovery-settings
api_get /v1/tables

PRESETS="$(kubectl exec deployment/table-maintenance-api \
  --namespace "${NAMESPACE}" \
  --context "${KUBE_CONTEXT}" \
  -- python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/v1/table-maintenance-presets', timeout=10).read().decode())")"
grep -q '"name":"default"' <<<"${PRESETS}" || { echo "preset default is not listed" >&2; exit 1; }

OLD_ROUTE_STATUS="$(kubectl exec deployment/table-maintenance-api \
  --namespace "${NAMESPACE}" \
  --context "${KUBE_CONTEXT}" \
  -- python -c "
import urllib.error, urllib.request
try:
    print(urllib.request.urlopen('http://localhost:8000/v1/policy-templates', timeout=10).status)
except urllib.error.HTTPError as e:
    print(e.code)")"
[[ "${OLD_ROUTE_STATUS}" == "404" ]] || { echo "/v1/policy-templates returned ${OLD_ROUTE_STATUS}, expected 404" >&2; exit 1; }

ADMIN_TOOLS="deployment/temporal-admintools"

for catalog in ${CATALOGS}; do
  kubectl exec "${ADMIN_TOOLS}" \
    --namespace temporal \
    --context "${KUBE_CONTEXT}" \
    -- temporal schedule describe \
    --address temporal-frontend.temporal.svc.cluster.local:7233 \
    --schedule-id "table-discovery:catalog=${catalog}" >/dev/null
done

ADMISSION_STATUS="$(kubectl exec "${ADMIN_TOOLS}" \
  --namespace temporal \
  --context "${KUBE_CONTEXT}" \
  -- temporal workflow describe \
  --address temporal-frontend.temporal.svc.cluster.local:7233 \
  --workflow-id table-maintenance-admission \
  --output json)"
grep -q '"status": "WORKFLOW_EXECUTION_STATUS_RUNNING"' <<<"${ADMISSION_STATUS}"

CONSUMER_GROUP="$(kubectl exec kafka-cluster-dual-role-0 \
  --namespace kafka \
  --context "${KUBE_CONTEXT}" \
  -- /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --group table-maintenance-event-consumer)"
awk '$2 == "polaris-catalog-events" && $7 != "-" && $7 != "" {found = 1} END {exit !found}' <<<"${CONSUMER_GROUP}"

kubectl wait --for=jsonpath='{.status.parents[0].conditions[?(@.type=="Accepted")].status}'=True httproute/console \
  --namespace "${NAMESPACE}" \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

( exec kubectl port-forward service/platform-gateway-istio "${GATEWAY_PORT}:80" \
    --namespace istio-ingress \
    --context "${KUBE_CONTEXT}" ) >/dev/null 2>&1 &
GATEWAY_PID=$!
GATEWAY_READY=""
for _ in $(seq 1 30); do
  if nc -z localhost "${GATEWAY_PORT}" 2>/dev/null; then
    GATEWAY_READY=1
    break
  fi
  sleep 1
done
[[ -n "${GATEWAY_READY}" ]] || { echo "gateway port-forward did not start" >&2; exit 1; }

GATEWAY_URL="http://localhost:${GATEWAY_PORT}"
for path in /console/ /console/tables/x/commits; do
  PAGE="$(curl -fsS "${GATEWAY_URL}${path}")"
  grep -qF '<div id="root">' <<<"${PAGE}" \
    || { echo "${path} through the gateway is not the console" >&2; exit 1; }
done
curl -fsS "${GATEWAY_URL}/console/api/v1/tables" | jq -e 'type == "array"' >/dev/null \
  || { echo "/console/api/v1/tables through the gateway is not a JSON array" >&2; exit 1; }
