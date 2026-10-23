#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel)"
source "${ROOT}/scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
NAMESPACE="lakehouse-control-plane"
CATALOG="iceberg"
SCHEMA="e2e"
ORDERS="tm_e2e_orders"
REGIONS="tm_e2e_regions"
TRINO_USER="tm-e2e"
TRINO_PORT="${TRINO_PORT:-18445}"
CERT_DIR="${ROOT}/platform/23-trino/client-certs/${TRINO_USER}"
MC_IMAGE="pgsty/mc:RELEASE.2026-10-18T00-00-00Z"
S3_ENDPOINT="http://rustfs.object-storage.svc.cluster.local:9000"
TEMPORAL_ADDRESS="temporal-frontend.temporal.svc.cluster.local:7233"
DISCOVERY_TIMEOUT_SECONDS="${DISCOVERY_TIMEOUT_SECONDS:-900}"
RUN_TIMEOUT_SECONDS="${RUN_TIMEOUT_SECONDS:-3600}"
EXPIRE_AGE_SECONDS=60
TRINO_PID=""

log::on_success "Table maintenance e2e passed"
log::on_failure "Table maintenance e2e failed"

cleanup() {
  if [[ -n "${TRINO_PID}" ]]; then
    kill "${TRINO_PID}" 2>/dev/null || true
  fi
}
trap '__log::on_exit $?; cleanup' EXIT

progress() {
  log::info "$1" >&3
}

api() {
  kubectl exec deployment/table-maintenance-api \
    --container api \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" \
    -- python -c '
import sys, urllib.error, urllib.request
method, path = sys.argv[1], sys.argv[2]
body = sys.argv[3].encode() if len(sys.argv) > 3 else None
request = urllib.request.Request("http://localhost:8000" + path, data=body, method=method)
request.add_header("Content-Type", "application/json")
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        print(response.read().decode())
except urllib.error.HTTPError as error:
    print(method, path, error.code, error.read().decode(), file=sys.stderr)
    sys.exit(1)
' "$@"
}

trino_sql() {
  ( exec kubectl port-forward service/trino "${TRINO_PORT}:8443" \
      --namespace lakehouse-query-engine \
      --context "${KUBE_CONTEXT}" ) >/dev/null 2>&1 &
  TRINO_PID=$!
  local ready=""
  for _ in $(seq 1 30); do
    if nc -z localhost "${TRINO_PORT}" 2>/dev/null; then
      ready=1
      break
    fi
    sleep 1
  done
  [[ -n "${ready}" ]] || { echo "Trino port-forward did not start" >&2; return 1; }
  local password rc=0
  password="$(cat "${CERT_DIR}/password.txt")"
  trino --server "https://localhost:${TRINO_PORT}" \
    --user "${TRINO_USER}" \
    --keystore-path "${CERT_DIR}/keystore.p12" \
    --keystore-password "${password}" \
    --truststore-path "${CERT_DIR}/truststore.p12" \
    --truststore-password "${password}" \
    --output-format TSV \
    --execute "$1" || rc=$?
  kill "${TRINO_PID}" 2>/dev/null || true
  wait "${TRINO_PID}" 2>/dev/null || true
  TRINO_PID=""
  return "${rc}"
}

trino_count() {
  trino_sql "SELECT count(*) FROM ${CATALOG}.${SCHEMA}.\"$1\"" | tail -n 1
}

temporal_cli() {
  kubectl exec deployment/temporal-admintools \
    --namespace temporal \
    --context "${KUBE_CONTEXT}" \
    -- temporal "$@" --address "${TEMPORAL_ADDRESS}"
}

object_count() {
  local prefix="$1" script overrides
  # shellcheck disable=SC2016
  script='mc alias set s3 "$S3_ENDPOINT" "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" >/dev/null
mc ls --recursive "s3/$PREFIX" | wc -l'
  overrides="$(jq -cn --arg image "${MC_IMAGE}" --arg script "${script}" \
    --arg endpoint "${S3_ENDPOINT}" --arg prefix "${prefix}" '{spec: {containers: [{
      name: "mc", image: $image, stdin: true,
      envFrom: [{secretRef: {name: "table-maintenance-s3"}}],
      env: [{name: "S3_ENDPOINT", value: $endpoint}, {name: "PREFIX", value: $prefix}],
      command: ["sh", "-ec", $script]}]}}')"
  kubectl run "tm-e2e-mc-$(date +%s)" \
    --rm -i --quiet \
    --restart Never \
    --image "${MC_IMAGE}" \
    --overrides "${overrides}" \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" \
    | tr -d '[:space:]'
}

data_prefix() {
  trino_sql "SELECT file_path FROM ${CATALOG}.${SCHEMA}.\"$1\$files\" WHERE content = 0 LIMIT 1" \
    | tail -n 1 \
    | sed -e 's#^s3://##' -e 's#/data/.*#/data/#'
}

table_uuid() {
  api GET "/v1/tables" \
    | jq -r --arg ns "${SCHEMA}" --arg t "$1" \
      '.[] | select(.catalog == "iceberg" and .namespace == $ns and .table == $t
        and (.status == "active" or .status == "paused")) | .uuid'
}

pause_table() {
  api POST "/v1/tables/$1/pause" >/dev/null
}

resume_table() {
  api POST "/v1/tables/$1/resume" >/dev/null
}

wait_for_table() {
  local table="$1" deadline uuid=""
  deadline=$(( $(date +%s) + DISCOVERY_TIMEOUT_SECONDS ))
  while (( $(date +%s) < deadline )); do
    uuid="$(table_uuid "${table}")"
    if [[ -n "${uuid}" ]]; then
      echo "${uuid}"
      return 0
    fi
    sleep 10
  done
  echo "table ${table} was not discovered within ${DISCOVERY_TIMEOUT_SECONDS}s" >&2
  return 1
}

run_ids() {
  api GET "/v1/tables/$1/runs?limit=500" | jq -c '[.[].run_id]'
}

wait_for_quiet_table() {
  local uuid="$1" deadline active
  deadline=$(( $(date +%s) + RUN_TIMEOUT_SECONDS ))
  while (( $(date +%s) < deadline )); do
    active="$(api GET "/v1/tables/${uuid}/runs?limit=500" \
      | jq '[.[] | select(.status == "pending" or .status == "running")] | length')"
    (( active == 0 )) && return 0
    sleep 15
  done
  echo "runs of ${uuid} still in flight after ${RUN_TIMEOUT_SECONDS}s" >&2
  return 1
}

wait_for_new_run() {
  local uuid="$1" before="$2" selector="$3" deadline runs found active
  deadline=$(( $(date +%s) + RUN_TIMEOUT_SECONDS ))
  while (( $(date +%s) < deadline )); do
    runs="$(api GET "/v1/tables/${uuid}/runs?limit=500" \
      | jq -c --argjson before "${before}" '[.[] | select(.run_id as $id | $before | index($id) | not)]')"
    found="$(jq -r "[.[] | select(${selector}) | select(.status != \"pending\" and .status != \"running\")] | .[0].run_id // empty" <<<"${runs}")"
    active="$(jq '[.[] | select(.status == "pending" or .status == "running")] | length' <<<"${runs}")"
    if [[ -n "${found}" ]] && (( active == 0 )); then
      echo "${runs}"
      return 0
    fi
    sleep 15
  done
  echo "no terminal run matching ${selector} for ${uuid} within ${RUN_TIMEOUT_SECONDS}s" >&2
  return 1
}

assert_runs_succeeded() {
  local label="$1" runs="$2" failed rewritten
  failed="$(jq -c '[.[] | .operations[] | select(.status != "succeeded")
    | {operation, status, error}]' <<<"${runs}")"
  if [[ "${failed}" != "[]" ]]; then
    echo "${label}: operations did not succeed: ${failed}" >&2
    return 1
  fi
  rewritten="$(jq '[.[] | .operations[] | select(.operation == "rewrite_data_files")
    | .metrics.rewritten_data_files_count // 0] | add // 0' <<<"${runs}")"
  if (( rewritten <= 0 )) && jq -e '[.[] | .operations[]
      | select(.operation == "rewrite_data_files") | .metrics.completed_without_callback]
      | any' <<<"${runs}" >/dev/null; then
    progress "${label}: the compaction callback was lost; relying on the \$files count check"
  elif (( rewritten <= 0 )); then
    echo "${label}: rewritten_data_files_count is ${rewritten}" >&2
    return 1
  fi
}

report_runs() {
  local label="$1" runs="$2" line
  while IFS= read -r line; do
    progress "${label} ${line}"
  done < <(jq -r '.[] | . as $run | .operations[] |
    "run \($run.run_id) \($run.trigger) \(.operation) \(.status) attempts=\(.attempts) \(.metrics | tojson)"' \
    <<<"${runs}")
}

assert_reconcile_running() {
  local uuid="$1" status
  status="$(temporal_cli workflow describe --workflow-id "table-reconcile-${uuid}" --output json \
    | jq -r '.workflowExecutionInfo.status')"
  [[ "${status}" == "WORKFLOW_EXECUTION_STATUS_RUNNING" ]] || {
    echo "table-reconcile-${uuid} is ${status}" >&2
    return 1
  }
  progress "table-reconcile-${uuid} is RUNNING"
}

assert_partition_filter() {
  local run_id="$1" filter
  filter="$(temporal_cli workflow show --workflow-id "maintenance-${run_id}" --output json \
    | jq -r '.events[0].workflowExecutionStartedEventAttributes.input.payloads[0].data
      | @base64d | fromjson
      | [.plan.operations[] | select(.operation == "rewrite_data_files") | .filters[]?.where]
      | map(select(. != null and . != "")) | .[0] // empty')"
  [[ -n "${filter}" ]] || { echo "run ${run_id} compacted without a where filter" >&2; return 1; }
  grep -qF "'o\\'neil'" <<<"${filter}" || {
    echo "run ${run_id} where filter lacks the escaped quote: ${filter}" >&2
    return 1
  }
  progress "regions where filter: ${filter}"
}

progress "issuing the Trino client certificate for ${TRINO_USER}"
task --dir "${ROOT}" trino:issue-cert \
  TRINO_USER="${TRINO_USER}" PRINT_USAGE=false KUBE_CONTEXT="${KUBE_CONTEXT}"

progress "ensuring the discovery rule ${CATALOG} / ${SCHEMA} / tm_e2e_*"
TEMPLATE_ID="$(api GET /v1/policy-templates | jq -r '.[] | select(.name == "default") | .id')"
[[ -n "${TEMPLATE_ID}" ]] || { echo "policy template default is missing" >&2; exit 1; }
RULE_ID="$(api GET /v1/discovery-rules | jq -r --arg ns "${SCHEMA}" \
  '.[] | select(.effect == "include" and .catalog_pattern == "iceberg"
    and .namespace_pattern == $ns and .table_pattern == "tm_e2e_*") | .id' | head -n 1)"
if [[ -z "${RULE_ID}" ]]; then
  RULE_ID="$(api POST /v1/discovery-rules "$(jq -cn --arg t "${TEMPLATE_ID}" --arg ns "${SCHEMA}" \
    '{priority: 10, effect: "include", catalog_pattern: "iceberg", namespace_pattern: $ns,
      table_pattern: "tm_e2e_*", template_id: $t, enabled: true}')" | jq -r '.id')"
fi
progress "discovery rule ${RULE_ID}"

progress "creating ${CATALOG}.${SCHEMA}.${ORDERS} and ${CATALOG}.${SCHEMA}.${REGIONS}"
trino_sql "CREATE SCHEMA IF NOT EXISTS ${CATALOG}.${SCHEMA};
CREATE TABLE IF NOT EXISTS ${CATALOG}.${SCHEMA}.${ORDERS} (
  id BIGINT, customer VARCHAR, amount DOUBLE, order_ts TIMESTAMP(6) WITH TIME ZONE
) WITH (partitioning = ARRAY['day(order_ts)', 'bucket(id, 4)']);
CREATE TABLE IF NOT EXISTS ${CATALOG}.${SCHEMA}.${REGIONS} (
  id BIGINT, region VARCHAR, note VARCHAR
) WITH (partitioning = ARRAY['region'])"

for table in "${ORDERS}" "${REGIONS}"; do
  uuid="$(table_uuid "${table}")"
  if [[ -n "${uuid}" ]]; then
    progress "pausing the registered ${table} ${uuid} while the e2e writes to it"
    pause_table "${uuid}"
  fi
done

progress "inserting 20 single-row orders, 8 single-row regions, and deleting one order"
STATEMENTS=""
for id in $(seq 1 20); do
  day=$(( id % 2 + 1 ))
  STATEMENTS+="INSERT INTO ${CATALOG}.${SCHEMA}.${ORDERS} VALUES
    (${id}, 'customer-${id}', ${id}.5, TIMESTAMP '2026-10-0${day} 10:00:00.000000 UTC');"
done
for id in $(seq 1 8); do
  if (( id % 2 == 0 )); then region="'o''neil'"; else region="'north'"; fi
  STATEMENTS+="INSERT INTO ${CATALOG}.${SCHEMA}.${REGIONS} VALUES (${id}, ${region}, 'note-${id}');"
done
STATEMENTS+="DELETE FROM ${CATALOG}.${SCHEMA}.${ORDERS} WHERE id = 3"
trino_sql "${STATEMENTS}"
LAST_WRITE_AT="$(date +%s)"

progress "waiting for discovery of both tables (up to ${DISCOVERY_TIMEOUT_SECONDS}s)"
ORDERS_UUID="$(wait_for_table "${ORDERS}")"
REGIONS_UUID="$(wait_for_table "${REGIONS}")"
for uuid in "${ORDERS_UUID}" "${REGIONS_UUID}"; do
  progress "table-reconcile-${uuid} current run started at $(temporal_cli workflow describe \
    --workflow-id "table-reconcile-${uuid}" --output json \
    | jq -r '.workflowExecutionInfo.startTime')"
done
progress "discovery schedule recent runs: $(temporal_cli schedule describe \
  --schedule-id "table-discovery-${CATALOG}" --output json \
  | jq -c '[.info.recentActions[]?.scheduleTime] | .[-3:]')"
progress "on a first run, a reconcile start before the next scheduled run means the event path found the table (describe shows the current run, which changes on continue-as-new)"

progress "pausing both tables and waiting for event-driven runs to settle"
pause_table "${ORDERS_UUID}"
pause_table "${REGIONS_UUID}"
wait_for_quiet_table "${ORDERS_UUID}"
wait_for_quiet_table "${REGIONS_UUID}"

progress "lowering ${ORDERS} thresholds while paused"
api PUT "/v1/tables/${ORDERS_UUID}/settings" "$(jq -cn --argjson age "${EXPIRE_AGE_SECONDS}" '{
  rewrite_data_files: {min_reducible_files: 2},
  rewrite_manifests: {min_small_manifests: 1},
  expire_snapshots: {older_than_seconds: $age, retain_last: 1},
  remove_orphan_files: {older_than_seconds: 86400}}')" >/dev/null
progress "setting ${REGIONS} to per-partition compaction while paused"
api PUT "/v1/tables/${REGIONS_UUID}/settings" '{"rewrite_data_files":
  {"scope": "partition", "min_reducible_files": 2, "min_interval_seconds": 60}}' >/dev/null

WAIT_SECONDS=$(( LAST_WRITE_AT + EXPIRE_AGE_SECONDS + 5 - $(date +%s) ))
if (( WAIT_SECONDS > 0 )); then
  sleep "${WAIT_SECONDS}"
fi

ORDERS_PREFIX="$(data_prefix "${ORDERS}")"
REGIONS_PREFIX="$(data_prefix "${REGIONS}")"
ORDERS_FILES_BEFORE="$(trino_count "${ORDERS}\$files")"
ORDERS_SNAPSHOTS_BEFORE="$(trino_count "${ORDERS}\$snapshots")"
ORDERS_OBJECTS_BEFORE="$(object_count "${ORDERS_PREFIX}")"
REGIONS_FILES_BEFORE="$(trino_count "${REGIONS}\$files")"
REGIONS_SNAPSHOTS_BEFORE="$(trino_count "${REGIONS}\$snapshots")"
REGIONS_OBJECTS_BEFORE="$(object_count "${REGIONS_PREFIX}")"
progress "before: ${ORDERS} files=${ORDERS_FILES_BEFORE} snapshots=${ORDERS_SNAPSHOTS_BEFORE} objects=${ORDERS_OBJECTS_BEFORE}"
progress "before: ${REGIONS} files=${REGIONS_FILES_BEFORE} snapshots=${REGIONS_SNAPSHOTS_BEFORE} objects=${REGIONS_OBJECTS_BEFORE}"

ORDERS_BEFORE_RUNS="$(run_ids "${ORDERS_UUID}")"
REGIONS_BEFORE_RUNS="$(run_ids "${REGIONS_UUID}")"

progress "resuming ${ORDERS} and triggering all four operations"
resume_table "${ORDERS_UUID}"
api POST "/v1/tables/${ORDERS_UUID}/maintenance" '{"operations": ["rewrite_data_files",
  "rewrite_manifests", "expire_snapshots", "remove_orphan_files"]}' >/dev/null

progress "resuming ${REGIONS} so the scheduled plan compacts through where filters"
resume_table "${REGIONS_UUID}"

progress "waiting for the ${ORDERS} manual run (up to ${RUN_TIMEOUT_SECONDS}s)"
ORDERS_RUNS="$(wait_for_new_run "${ORDERS_UUID}" "${ORDERS_BEFORE_RUNS}" '.trigger == "manual"')"
report_runs "${ORDERS}" "${ORDERS_RUNS}"
assert_runs_succeeded "${ORDERS}" "${ORDERS_RUNS}"
jq -e '[.[] | select(.trigger == "manual") | .operations[].operation] | unique | length == 4' \
  <<<"${ORDERS_RUNS}" >/dev/null || { echo "manual run lacks an operation" >&2; exit 1; }

progress "waiting for the ${REGIONS} scheduled compaction run"
REGIONS_RUNS="$(wait_for_new_run "${REGIONS_UUID}" "${REGIONS_BEFORE_RUNS}" \
  '.trigger == "scheduled" and any(.operations[]; .operation == "rewrite_data_files")')"
report_runs "${REGIONS}" "${REGIONS_RUNS}"
assert_runs_succeeded "${REGIONS}" "${REGIONS_RUNS}"
REGIONS_RUN_ID="$(jq -r '[.[] | select(any(.operations[]; .operation == "rewrite_data_files"))]
  | .[0].run_id' <<<"${REGIONS_RUNS}")"
assert_partition_filter "${REGIONS_RUN_ID}"

ORDERS_FILES_AFTER="$(trino_count "${ORDERS}\$files")"
ORDERS_SNAPSHOTS_AFTER="$(trino_count "${ORDERS}\$snapshots")"
ORDERS_OBJECTS_AFTER="$(object_count "${ORDERS_PREFIX}")"
REGIONS_FILES_AFTER="$(trino_count "${REGIONS}\$files")"
REGIONS_SNAPSHOTS_AFTER="$(trino_count "${REGIONS}\$snapshots")"
REGIONS_OBJECTS_AFTER="$(object_count "${REGIONS_PREFIX}")"
progress "after: ${ORDERS} files=${ORDERS_FILES_AFTER} snapshots=${ORDERS_SNAPSHOTS_AFTER} objects=${ORDERS_OBJECTS_AFTER}"
progress "after: ${REGIONS} files=${REGIONS_FILES_AFTER} snapshots=${REGIONS_SNAPSHOTS_AFTER} objects=${REGIONS_OBJECTS_AFTER}"

(( ORDERS_FILES_AFTER < ORDERS_FILES_BEFORE )) \
  || { echo "${ORDERS} file count did not decrease" >&2; exit 1; }
(( ORDERS_SNAPSHOTS_AFTER < ORDERS_SNAPSHOTS_BEFORE )) \
  || { echo "${ORDERS} snapshot count did not decrease" >&2; exit 1; }
if jq -e '[.[] | .operations[] | .metrics.completed_without_callback] | any' \
    <<<"${ORDERS_RUNS}" >/dev/null; then
  progress "${ORDERS}: a callback was lost; skipping the RustFS object accounting"
else
  ADDED="$(jq '[.[] | .operations[] | select(.operation == "rewrite_data_files")
    | .metrics.added_data_files_count // 0] | add // 0' <<<"${ORDERS_RUNS}")"
  DELETED="$(jq '[.[] | .operations[] | select(.operation == "expire_snapshots") | .metrics
    | (.deleted_data_files_count // 0) + (.deleted_position_delete_files_count // 0)
      + (.deleted_equality_delete_files_count // 0)] | add // 0' <<<"${ORDERS_RUNS}")"
  EXPECTED=$(( ORDERS_OBJECTS_BEFORE + ADDED - DELETED ))
  progress "${ORDERS} objects: ${ORDERS_OBJECTS_BEFORE} + ${ADDED} added - ${DELETED} expired = ${EXPECTED}"
  (( DELETED > 0 )) \
    || { echo "${ORDERS} expire_snapshots deleted no files" >&2; exit 1; }
  (( ORDERS_OBJECTS_AFTER <= EXPECTED )) \
    || { echo "${ORDERS} has ${ORDERS_OBJECTS_AFTER} objects, expected <= ${EXPECTED}" >&2; exit 1; }
fi
(( REGIONS_FILES_AFTER < REGIONS_FILES_BEFORE )) \
  || { echo "${REGIONS} file count did not decrease" >&2; exit 1; }

assert_reconcile_running "${ORDERS_UUID}"
assert_reconcile_running "${REGIONS_UUID}"
