#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/gateway.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"
NAMESPACE="lakehouse-control-plane"

log::on_success "Lakehouse control plane is ready"
log::on_failure "Lakehouse control plane is not ready"

namespace::assert_ambient lakehouse-control-plane
namespace::assert_ambient lakehouse-maintenance-operations


for namespace in "${NAMESPACE}" lakehouse-maintenance-operations; do
  kubectl wait "namespace/${namespace}" \
    --for jsonpath='{.status.phase}'=Active \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
done

for deployment in table-maintenance-api table-maintenance-worker \
  table-maintenance-event-consumer table-maintenance-console; do
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

helm test table-maintenance \
  --namespace "${NAMESPACE}" \
  --kube-context "${KUBE_CONTEXT}" \
  --timeout "${HELM_TEST_TIMEOUT:-120s}"

WORKER_CONFIG="$(kubectl get configmap table-maintenance-worker-config \
  --output 'jsonpath={.data.config\.yaml}' \
  --namespace "${NAMESPACE}" \
  --context "${KUBE_CONTEXT}")"
for key in queue urgent_queue; do
  queue="$(yq ".spark.volcano.${key}" <<<"${WORKER_CONFIG}")"
  [[ -n "${queue}" && "${queue}" != "null" ]] \
    || { echo "spark.volcano.${key} is not set in table-maintenance-worker-config" >&2; exit 1; }
  kubectl wait "queue.scheduling.volcano.sh/${queue}" \
    --for jsonpath='{.status.state}'=Open \
    --timeout 60s \
    --context "${KUBE_CONTEXT}"
  queue_memory="$(kubectl get "queue.scheduling.volcano.sh/${queue}" \
    --output jsonpath='{.spec.capability.memory}' \
    --context "${KUBE_CONTEXT}")"
  [[ "${queue_memory}" == "5017Mi" ]] \
    || { echo "queue ${queue} capability memory is ${queue_memory}, expected 5017Mi" >&2; exit 1; }
done

PRIORITY_CLASS_PREFIX="$(yq '.spark.volcano.priority_class_prefix' <<<"${WORKER_CONFIG}")"
[[ -n "${PRIORITY_CLASS_PREFIX}" && "${PRIORITY_CLASS_PREFIX}" != "null" ]] \
  || { echo "spark.volcano.priority_class_prefix is not set in table-maintenance-worker-config" >&2; exit 1; }
for priority in p0 p1 p2 p3; do
  preemption_policy="$(kubectl get "priorityclass/${PRIORITY_CLASS_PREFIX}-${priority}" \
    --output jsonpath='{.preemptionPolicy}' \
    --context "${KUBE_CONTEXT}")"
  [[ "${preemption_policy}" == "Never" ]] \
    || { echo "priorityclass ${PRIORITY_CLASS_PREFIX}-${priority} preemptionPolicy is ${preemption_policy}, expected Never" >&2; exit 1; }
done

api_get() {
  kubectl exec deployment/table-maintenance-api \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" \
    -- python -c "import sys, urllib.request; r = urllib.request.urlopen('http://localhost:8000' + sys.argv[1], timeout=10); print(sys.argv[1], r.status)" "$1"
}

api_body() {
  kubectl exec deployment/table-maintenance-api \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" \
    -- python -c "import sys, urllib.request; print(urllib.request.urlopen('http://localhost:8000' + sys.argv[1], timeout=10).read().decode())" "$1"
}

api_get /healthz
api_get /v1/discovery-policies
api_get /v1/scanned-catalogs
api_get /v1/maintenance-policies/default
api_get /v1/tables
api_get /v1/catalogs

DEFAULT_POLICY="$(api_body /v1/maintenance-policies/default)"
grep -q '"name":"default"' <<<"${DEFAULT_POLICY}" || { echo "policy default is missing" >&2; exit 1; }

for old_route in /v1/policy-templates /v1/compaction-rounds /v1/discovery-rules /v1/discovery-policies/default; do
  OLD_ROUTE_STATUS="$(kubectl exec deployment/table-maintenance-api \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" \
    -- python -c "
import urllib.error, urllib.request
try:
    print(urllib.request.urlopen('http://localhost:8000${old_route}', timeout=10).status)
except urllib.error.HTTPError as e:
    print(e.code)")"
  [[ "${OLD_ROUTE_STATUS}" == "404" ]] || { echo "${old_route} returned ${OLD_ROUTE_STATUS}, expected 404" >&2; exit 1; }
done

ADMIN_TOOLS="deployment/temporal-admintools"

temporal_admin() {
  kubectl exec "${ADMIN_TOOLS}" \
    --namespace temporal \
    --context "${KUBE_CONTEXT}" \
    -- temporal "$@" \
    --address temporal-frontend.temporal.svc.cluster.local:7233
}

DISCOVERY_SCHEDULE="table-discovery"
CATALOG_SCHEDULE_PREFIX="table-discovery:catalog="
DISCOVERY_SCHEDULES=""
for _ in $(seq 1 30); do
  DISCOVERY_SCHEDULES="$(temporal_admin schedule list --output json \
    | jq -r --arg prefix "${DISCOVERY_SCHEDULE}" \
      '(if type == "array" then .[] else . end) | (.scheduleId // .id // empty) | select(startswith($prefix))' \
    | sort -u)"
  [[ "${DISCOVERY_SCHEDULES}" == "${DISCOVERY_SCHEDULE}" ]] && break
  sleep 2
done
CATALOG_SCHEDULES="$(grep -F "${CATALOG_SCHEDULE_PREFIX}" <<<"${DISCOVERY_SCHEDULES}" | xargs || true)"
[[ -z "${CATALOG_SCHEDULES}" ]] \
  || { echo "per-catalog discovery schedules remain: ${CATALOG_SCHEDULES}" >&2; exit 1; }
[[ "${DISCOVERY_SCHEDULES}" == "${DISCOVERY_SCHEDULE}" ]] \
  || { echo "expected exactly one schedule ${DISCOVERY_SCHEDULE}, found: $(xargs <<<"${DISCOVERY_SCHEDULES}")" >&2; exit 1; }
DESCRIBED_SCHEDULE="$(temporal_admin schedule describe --output json --schedule-id "${DISCOVERY_SCHEDULE}")"
jq -e '[.. | objects | .paused] | any(. == true) | not' <<<"${DESCRIBED_SCHEDULE}" >/dev/null \
  || { echo "schedule ${DISCOVERY_SCHEDULE} is paused" >&2; exit 1; }

if RETIRED_WORKFLOW="$(temporal_admin workflow describe --workflow-id table-maintenance-admission 2>&1)"; then
  echo "workflow table-maintenance-admission exists, expected it to be gone" >&2
  exit 1
fi
grep -qiE 'workflow not found' <<<"${RETIRED_WORKFLOW}" \
  || { echo "describing workflow table-maintenance-admission failed for another reason: ${RETIRED_WORKFLOW}" >&2; exit 1; }

if RETIRED_SCHEDULE="$(temporal_admin schedule describe --schedule-id compaction-rounds 2>&1)"; then
  echo "schedule compaction-rounds exists, expected it to be gone" >&2
  exit 1
fi
grep -qiE '(schedule|workflow) not found' <<<"${RETIRED_SCHEDULE}" \
  || { echo "describing schedule compaction-rounds failed for another reason: ${RETIRED_SCHEDULE}" >&2; exit 1; }

CONSUMER_GROUP="$(kubectl exec kafka-cluster-dual-role-0 \
  --namespace kafka \
  --context "${KUBE_CONTEXT}" \
  -- /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --group table-maintenance-event-consumer)"
awk '$2 == "polaris-catalog-events" && $7 != "-" && $7 != "" {found = 1} END {exit !found}' <<<"${CONSUMER_GROUP}"

gateway::assert_routes_allowed "${NAMESPACE}"
gateway::assert_route_accepted "${NAMESPACE}" table-maintenance-console
for path in /console /console/ /console/catalogs; do
  PAGE="$(gateway::curl "${path}" -fsSL)"
  grep -qF '<div id="root">' <<<"${PAGE}" \
    || { echo "${path} through the gateway is not the console" >&2; exit 1; }
done
gateway::curl /console/api/v1/tables -fsS | jq -e 'type == "array"' >/dev/null \
  || { echo "/console/api/v1/tables through the gateway is not a JSON array" >&2; exit 1; }

gateway::assert_route_accepted "${NAMESPACE}" table-maintenance-api
gateway::curl /api/openapi.json -fsS | jq -e '.servers == [{"url": "/api"}]' >/dev/null \
  || { echo "/api/openapi.json through the gateway does not name /api as its server" >&2; exit 1; }
DOCS="$(gateway::curl /api/docs -fsS)"
grep -qF "'/api/openapi.json'" <<<"${DOCS}" \
  ||{ echo "/api/docs through the gateway does not load /api/openapi.json" >&2; exit 1; }
gateway::curl /api/v1/tables -fsS | jq -e 'type == "array"' >/dev/null \
  || { echo "/api/v1/tables through the gateway is not a JSON array" >&2; exit 1; }
