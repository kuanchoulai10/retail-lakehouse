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
RT_BUCKET="tm-e2e-catalogs"
RT_CATALOG=""

log::on_success "Table maintenance e2e passed"
log::on_failure "Table maintenance e2e failed"

cleanup() {
  if [[ -n "${TRINO_PID}" ]]; then
    kill "${TRINO_PID}" 2>/dev/null || true
  fi
  if [[ -n "${RT_CATALOG}" ]]; then
    drop_round_trip_catalog || echo "could not drop the round-trip catalog ${RT_CATALOG}" >&2
    remove_prefix "${RT_BUCKET}/${RT_CATALOG}/" \
      || echo "could not remove s3://${RT_BUCKET}/${RT_CATALOG}/" >&2
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

api_call() {
  kubectl exec deployment/table-maintenance-api \
    --container api \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" \
    -- python -c '
import json, sys, urllib.error, urllib.request
method, path = sys.argv[1], sys.argv[2]
body = sys.argv[3].encode() if len(sys.argv) > 3 else None
request = urllib.request.Request("http://localhost:8000" + path, data=body, method=method)
request.add_header("Content-Type", "application/json")
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        status, text = response.status, response.read().decode()
except urllib.error.HTTPError as error:
    status, text = error.code, error.read().decode()
print(json.dumps({"status": status, "body": json.loads(text) if text else None}))
' "$@"
}

POLARIS_PY_PRELUDE='
import json, os, sys, urllib.error, urllib.parse, urllib.request
CATALOG_API = os.environ["GLAC_CATALOG__URI"].rstrip("/")
MANAGEMENT_API = os.environ["GLAC_CATALOG__MANAGEMENT_URI"].rstrip("/")
_id, _, _secret = os.environ["GLAC_CATALOG__CREDENTIAL"].partition(":")
_form = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": _id,
    "client_secret": _secret, "scope": os.environ["GLAC_CATALOG__SCOPE"]}).encode()
with urllib.request.urlopen(CATALOG_API + "/v1/oauth/tokens", data=_form, timeout=30) as _reply:
    _token = json.load(_reply)["access_token"]
del _id, _secret, _form

def polaris(base, method, path, body=None):
    request = urllib.request.Request(base + path, data=body, method=method)
    request.add_header("Authorization", "Bearer " + _token)
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status, text = response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        status, text = error.code, error.read().decode()
    payload = json.loads(text) if text else None
    if isinstance(payload, dict):
        payload.pop("config", None)
    return status, payload

def q(value):
    return urllib.parse.quote(value, safe="")
'

polaris() {
  kubectl exec deployment/table-maintenance-api \
    --container api \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" \
    -- python -c "${POLARIS_PY_PRELUDE}"'
api, method, path = sys.argv[1], sys.argv[2], sys.argv[3]
body = sys.argv[4].encode() if len(sys.argv) > 4 else None
status, payload = polaris(CATALOG_API if api == "catalog" else MANAGEMENT_API, method, path, body)
print(json.dumps({"status": status, "body": payload}))
' "$@"
}

drop_round_trip_catalog() {
  kubectl exec deployment/table-maintenance-api \
    --container api \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" \
    -- python -c "${POLARIS_PY_PRELUDE}"'
catalog = sys.argv[1]
if polaris(MANAGEMENT_API, "GET", "/catalogs/" + q(catalog))[0] == 404:
    sys.exit(0)

def namespaces(parent):
    query = "?parent=" + q("\x1f".join(parent)) if parent else ""
    _, body = polaris(CATALOG_API, "GET", "/v1/" + q(catalog) + "/namespaces" + query)
    found = []
    for child in (body or {}).get("namespaces", []):
        found.extend(namespaces(child))
        found.append(child)
    return found

for parts in namespaces([]):
    ns = q("\x1f".join(parts))
    for prefix, kind, suffix in (("/v1/", "views", ""), ("/polaris/v1/", "generic-tables", ""),
                                 ("/v1/", "tables", "?purgeRequested=false")):
        listing = prefix + q(catalog) + "/namespaces/" + ns + "/" + kind
        _, body = polaris(CATALOG_API, "GET", listing)
        for identifier in (body or {}).get("identifiers", []):
            polaris(CATALOG_API, "DELETE", listing + "/" + q(identifier["name"]) + suffix)
    polaris(CATALOG_API, "DELETE", "/v1/" + q(catalog) + "/namespaces/" + ns)
_, body = polaris(MANAGEMENT_API, "GET", "/catalogs/" + q(catalog) + "/catalog-roles")
for role in (body or {}).get("roles", []):
    if role["name"] != "catalog_admin":
        polaris(MANAGEMENT_API, "DELETE", "/catalogs/" + q(catalog) + "/catalog-roles/" + q(role["name"]))
status, body = polaris(MANAGEMENT_API, "DELETE", "/catalogs/" + q(catalog))
print("dropped catalog", catalog, status, json.dumps(body) if body else "", file=sys.stderr)
sys.exit(0 if status in (204, 404) else 1)
' "${RT_CATALOG}"
}

check() {
  local filter="$1" json="$2" message="$3"
  shift 3
  jq -e "$@" "${filter}" <<<"${json}" >/dev/null || {
    echo "${message}: $(jq -c . <<<"${json}")" >&2
    return 1
  }
}

expect_gone() {
  local api="$1" path="$2" label="$3" reply
  reply="$(polaris "${api}" GET "${path}")"
  check '.status == 404' "${reply}" "${label} still exists in Polaris after the delete"
  progress "catalog round trip: ${label} deleted, Polaris answers 404"
}

# shellcheck disable=SC2016
catalog_round_trip() {
  local catalog ns child base iceberg storage reply created version uuid location stale
  catalog="tm_e2e_catalog_$(date +%s)"
  ns="tm_e2e"
  child="tm_e2e%1Fa.b"
  iceberg="$(api GET "/v1/catalogs/${CATALOG}")"
  base="s3://${RT_BUCKET}/${catalog}"
  storage="$(jq -c --arg base "${base}" '.storage_config | {storage_type, allowed_locations: [$base],
    endpoint, sts_endpoint, path_style_access}' <<<"${iceberg}")"

  progress "catalog round trip: creating ${catalog} at ${base}"
  ensure_bucket "${RT_BUCKET}"
  RT_CATALOG="${catalog}"
  created="$(api POST /v1/catalogs "$(jq -cn --arg name "${catalog}" --arg base "${base}" \
    --argjson storage "${storage}" '{name: $name, type: "INTERNAL", default_base_location: $base,
      storage_config: $storage}')")"
  reply="$(polaris management GET "/catalogs/${catalog}")"
  check '.status == 200 and .body.type == "INTERNAL"
    and .body.properties["default-base-location"] == $base
    and any(.body.storageConfigInfo.allowedLocations[]; rtrimstr("/") == $base)' \
    "${reply}" "Polaris does not hold the catalog as written" --arg base "${base}"
  reply="$(polaris management GET "/catalogs/${catalog}/catalog-roles/catalog_admin/grants")"
  check 'any(.body.grants[]; .type == "catalog" and .privilege == "CATALOG_MANAGE_CONTENT")' \
    "${reply}" "catalog_admin of ${catalog} lacks CATALOG_MANAGE_CONTENT"
  progress "catalog round trip: catalog_admin holds CATALOG_MANAGE_CONTENT"
  check 'any(.[]; .name == $c)' "$(api GET /v1/catalogs)" "the catalog list lacks ${catalog}" \
    --arg c "${catalog}"

  version="$(jq '.entity_version' <<<"${created}")"
  api PUT "/v1/catalogs/${catalog}" "$(jq -cn --argjson v "${version}" --arg base "${base}" \
    --argjson storage "${storage}" '{entity_version: $v, default_base_location: $base,
      properties: {"tm-e2e": "updated"}, storage_config: $storage}')" >/dev/null
  reply="$(polaris management GET "/catalogs/${catalog}")"
  check '.body.properties["tm-e2e"] == "updated"' "${reply}" "the catalog update did not reach Polaris"
  stale="$(api_call PUT "/v1/catalogs/${catalog}" "$(jq -cn --argjson v "${version}" \
    --arg base "${base}" --argjson storage "${storage}" '{entity_version: $v,
      default_base_location: $base, properties: {"tm-e2e": "stale"}, storage_config: $storage}')")"
  reply="$(polaris management PUT "/catalogs/${catalog}" "$(jq -cn --argjson v "${version}" \
    '{currentEntityVersion: $v, properties: {"tm-e2e": "stale"}}')")"
  progress "catalog round trip: Polaris stale catalog update: $(jq -c . <<<"${reply}")"
  progress "catalog round trip: our stale catalog update: $(jq -c . <<<"${stale}")"
  check '$polaris.status == 409 and ($polaris.body.error.message | length > 0)' "${stale}" \
    "Polaris did not refuse the stale catalog update with a 409 message" --argjson polaris "${reply}"
  check '.status == 409 and (.body.detail | endswith("changed since you loaded it, reload"))' \
    "${stale}" "a stale catalog update is not our 409 reload message"

  progress "catalog round trip: namespaces [${ns}] and [${ns}, a.b]"
  api POST "/v1/catalogs/${catalog}/namespaces" \
    '{"namespace": ["tm_e2e"], "properties": {"owner": "tm-e2e"}}' >/dev/null
  api POST "/v1/catalogs/${catalog}/namespaces" '{"namespace": ["tm_e2e", "a.b"]}' >/dev/null
  reply="$(polaris catalog GET "/v1/${catalog}/namespaces/${child}")"
  check '.status == 200 and .body.namespace == ["tm_e2e", "a.b"]' "${reply}" \
    "Polaris does not hold the namespace [tm_e2e, a.b]"
  check 'any(.[]; .namespace == ["tm_e2e"])' "$(api GET "/v1/catalogs/${catalog}/namespaces")" \
    "the namespace list lacks [tm_e2e]"
  check 'any(.[]; .namespace == ["tm_e2e", "a.b"])' \
    "$(api GET "/v1/catalogs/${catalog}/namespaces?parent=${ns}")" "the child list lacks [tm_e2e, a.b]"
  api PUT "/v1/catalogs/${catalog}/namespaces/${ns}/properties" \
    '{"updates": {"stage": "round-trip"}, "removals": ["owner"]}' >/dev/null
  reply="$(polaris catalog GET "/v1/${catalog}/namespaces/${ns}")"
  check '.body.properties.stage == "round-trip" and (.body.properties | has("owner") | not)' \
    "${reply}" "the namespace properties update did not reach Polaris"

  location="${base}/tm_e2e/a.b/rt_orders_custom"
  progress "catalog round trip: table rt_orders at ${location}, partitioned by day(order_ts)"
  created="$(api POST "/v1/catalogs/${catalog}/namespaces/${child}/tables" "$(jq -cn \
    --arg location "${location}" '{name: "rt_orders",
      schema_fields: [{name: "id", type: "long"}, {name: "order_ts", type: "timestamptz", required: false}],
      partition_fields: [{source_column: "order_ts", transform: "day"}],
      location: $location, properties: {"tm-e2e": "created"}}')")"
  uuid="$(jq -r '.uuid' <<<"${created}")"
  reply="$(polaris catalog GET "/v1/${catalog}/namespaces/${child}/tables/rt_orders")"
  check '.body.metadata as $m | .status == 200 and $m["table-uuid"] == $uuid
    and $m.location == $location and $m.properties["tm-e2e"] == "created"
    and ([$m.schemas[] | select(.["schema-id"] == $m["current-schema-id"]) | .fields[]
      | [.name, .type, .required]] == [["id", "long", true], ["order_ts", "timestamptz", false]])
    and ([$m["partition-specs"][] | select(.["spec-id"] == $m["default-spec-id"]) | .fields[]
      | .transform] == ["day"])' \
    "${reply}" "Polaris does not hold the table as written" --arg uuid "${uuid}" --arg location "${location}"
  check 'any(.[]; .name == "rt_orders")' \
    "$(api GET "/v1/catalogs/${catalog}/namespaces/${child}/tables")" "the table list lacks rt_orders"
  api PUT "/v1/catalogs/${catalog}/namespaces/${child}/tables/rt_orders/properties" "$(jq -cn \
    --arg uuid "${uuid}" '{expected_uuid: $uuid, updates: {"tm-e2e": "updated"}}')" >/dev/null
  reply="$(polaris catalog GET "/v1/${catalog}/namespaces/${child}/tables/rt_orders")"
  check '.body.metadata.properties["tm-e2e"] == "updated"' "${reply}" \
    "the table properties update did not reach Polaris"
  stale="$(api_call PUT "/v1/catalogs/${catalog}/namespaces/${child}/tables/rt_orders/properties" \
    '{"expected_uuid": "00000000-0000-0000-0000-000000000000", "updates": {"tm-e2e": "stale"}}')"
  progress "catalog round trip: our table update with another uuid: $(jq -c . <<<"${stale}")"
  check '.status == 409 and (.body.detail | endswith("changed since you loaded it, reload"))' \
    "${stale}" "a table update with another uuid is not our 409 reload message"
  api POST "/v1/catalogs/${catalog}/namespaces/${child}/tables/rt_orders/rename" \
    '{"target_namespace": ["tm_e2e", "a.b"], "target_name": "rt_orders_renamed"}' >/dev/null
  expect_gone catalog "/v1/${catalog}/namespaces/${child}/tables/rt_orders" "the old name rt_orders"
  reply="$(polaris catalog GET "/v1/${catalog}/namespaces/${child}/tables/rt_orders_renamed")"
  check '.status == 200 and .body.metadata["table-uuid"] == $uuid' "${reply}" \
    "the renamed table is not the same table in Polaris" --arg uuid "${uuid}"

  progress "catalog round trip: generic table rt_generic"
  api POST "/v1/catalogs/${catalog}/namespaces/${child}/generic-tables" "$(jq -cn \
    --arg location "${base}/tm_e2e/a.b/rt_generic" '{name: "rt_generic", format: "delta",
      base_location: $location, doc: "round trip", properties: {"tm-e2e": "created"}}')" >/dev/null
  reply="$(polaris catalog GET "/polaris/v1/${catalog}/namespaces/${child}/generic-tables/rt_generic")"
  check '.status == 200 and .body.table.format == "delta" and .body.table["base-location"] == $location
    and .body.table.doc == "round trip" and .body.table.properties["tm-e2e"] == "created"' \
    "${reply}" "Polaris does not hold the generic table as written" \
    --arg location "${base}/tm_e2e/a.b/rt_generic"
  check 'any(.[]; .name == "rt_generic")' \
    "$(api GET "/v1/catalogs/${catalog}/namespaces/${child}/generic-tables")" \
    "the generic table list lacks rt_generic"

  progress "catalog round trip: view rt_view"
  api POST "/v1/catalogs/${catalog}/namespaces/${child}/views" \
    '{"name": "rt_view", "sql": "SELECT 1 AS one", "dialect": "spark"}' >/dev/null
  reply="$(polaris catalog GET "/v1/${catalog}/namespaces/${child}/views/rt_view")"
  check '.body.metadata as $m
    | ([$m.versions[] | select(.["version-id"] == $m["current-version-id"])][0]) as $v
    | .status == 200
      and $v.representations == [{type: "sql", sql: "SELECT 1 AS one", dialect: "spark"}]
      and ([$m.schemas[] | select(.["schema-id"] == $v["schema-id"]) | .fields | length] == [0])' \
    "${reply}" "Polaris does not hold the view as written"
  check 'any(.[]; .name == "rt_view")' \
    "$(api GET "/v1/catalogs/${catalog}/namespaces/${child}/views")" "the view list lacks rt_view"

  stale="$(api_call DELETE "/v1/catalogs/${catalog}/namespaces/${child}")"
  reply="$(polaris catalog DELETE "/v1/${catalog}/namespaces/${child}")"
  progress "catalog round trip: Polaris non-empty namespace delete: $(jq -c . <<<"${reply}")"
  progress "catalog round trip: our non-empty namespace delete: $(jq -c . <<<"${stale}")"
  check '.status == $polaris.status and .body.detail == $polaris.body.error.message' "${stale}" \
    "our non-empty namespace delete does not pass the Polaris status and message" \
    --argjson polaris "${reply}"

  api DELETE "/v1/catalogs/${catalog}/namespaces/${child}/views/rt_view" >/dev/null
  expect_gone catalog "/v1/${catalog}/namespaces/${child}/views/rt_view" "view rt_view"
  api DELETE "/v1/catalogs/${catalog}/namespaces/${child}/generic-tables/rt_generic" >/dev/null
  expect_gone catalog "/polaris/v1/${catalog}/namespaces/${child}/generic-tables/rt_generic" \
    "generic table rt_generic"
  api DELETE "/v1/catalogs/${catalog}/namespaces/${child}/tables/rt_orders_renamed" >/dev/null
  expect_gone catalog "/v1/${catalog}/namespaces/${child}/tables/rt_orders_renamed" \
    "table rt_orders_renamed"
  api DELETE "/v1/catalogs/${catalog}/namespaces/${child}" >/dev/null
  expect_gone catalog "/v1/${catalog}/namespaces/${child}" "namespace [tm_e2e, a.b]"
  api DELETE "/v1/catalogs/${catalog}/namespaces/${ns}" >/dev/null
  expect_gone catalog "/v1/${catalog}/namespaces/${ns}" "namespace [tm_e2e]"
  api DELETE "/v1/catalogs/${catalog}" >/dev/null
  expect_gone management "/catalogs/${catalog}" "catalog ${catalog}"
  RT_CATALOG=""
  remove_prefix "${RT_BUCKET}/${catalog}/"
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

mc_run() {
  local script="$1" prefix="$2" overrides pod phase="" rc=1
  overrides="$(jq -cn --arg image "${MC_IMAGE}" --arg script "${script}" \
    --arg endpoint "${S3_ENDPOINT}" --arg prefix "${prefix}" '{spec: {containers: [{
      name: "mc", image: $image,
      envFrom: [{secretRef: {name: "table-maintenance-s3"}}],
      env: [{name: "S3_ENDPOINT", value: $endpoint}, {name: "PREFIX", value: $prefix}],
      command: ["sh", "-ec", $script]}]}}')"
  pod="tm-e2e-mc-$(date +%s)"
  if kubectl run "${pod}" \
      --restart Never \
      --image "${MC_IMAGE}" \
      --overrides "${overrides}" \
      --namespace "${NAMESPACE}" \
      --context "${KUBE_CONTEXT}" >/dev/null; then
    for _ in $(seq 1 120); do
      phase="$(kubectl get "pod/${pod}" \
        --output jsonpath='{.status.phase}' \
        --namespace "${NAMESPACE}" \
        --context "${KUBE_CONTEXT}")" || phase=""
      [[ "${phase}" == "Succeeded" || "${phase}" == "Failed" ]] && break
      sleep 1
    done
  fi
  if [[ "${phase}" == "Succeeded" ]]; then
    kubectl logs "pod/${pod}" \
      --namespace "${NAMESPACE}" \
      --context "${KUBE_CONTEXT}" && rc=0
  fi
  kubectl delete "pod/${pod}" \
    --ignore-not-found \
    --wait=false \
    --namespace "${NAMESPACE}" \
    --context "${KUBE_CONTEXT}" >/dev/null || true
  return "${rc}"
}

object_count() {
  local prefix="$1" script count
  # shellcheck disable=SC2016
  script='mc alias set s3 "$S3_ENDPOINT" "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" >/dev/null
mc ls --recursive "s3/$PREFIX" | wc -l'
  for _ in 1 2 3; do
    count="$(mc_run "${script}" "${prefix}" | tr -d '[:space:]')" || count=""
    if [[ "${count}" =~ ^[0-9]+$ ]]; then
      echo "${count}"
      return 0
    fi
    sleep 5
  done
  echo "object count of ${prefix} failed after 3 attempts" >&2
  return 1
}

ensure_bucket() {
  local bucket="$1" script
  # shellcheck disable=SC2016
  script='mc alias set s3 "$S3_ENDPOINT" "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" >/dev/null
mc mb --ignore-existing "s3/$PREFIX" >/dev/null'
  for _ in 1 2 3; do
    mc_run "${script}" "${bucket}" >/dev/null && return 0
    sleep 5
  done
  echo "could not create the bucket ${bucket} after 3 attempts" >&2
  return 1
}

remove_prefix() {
  local prefix="$1" script
  # shellcheck disable=SC2016
  script='mc alias set s3 "$S3_ENDPOINT" "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" >/dev/null
mc rm --recursive --force "s3/$PREFIX" >/dev/null'
  mc_run "${script}" "${prefix}" >/dev/null
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
  api GET "/v1/tables/$1/table-maintenance-runs?limit=500" | jq -c '[.[].run_id]'
}

wait_for_quiet_table() {
  local uuid="$1" deadline active
  deadline=$(( $(date +%s) + RUN_TIMEOUT_SECONDS ))
  while (( $(date +%s) < deadline )); do
    active="$(api GET "/v1/tables/${uuid}/table-maintenance-runs?limit=500" \
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
    runs="$(api GET "/v1/tables/${uuid}/table-maintenance-runs?limit=500" \
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
  status="$(temporal_cli workflow describe --workflow-id "table-reconciliation:table-uuid=${uuid}" \
    --output json | jq -r '.workflowExecutionInfo.status')"
  [[ "${status}" == "WORKFLOW_EXECUTION_STATUS_RUNNING" ]] || {
    echo "table-reconciliation:table-uuid=${uuid} is ${status}" >&2
    return 1
  }
  progress "table-reconciliation:table-uuid=${uuid} is RUNNING"
}

assert_partition_filter() {
  local run_id="$1" execution_ref filter
  execution_ref="$(api GET "/v1/table-maintenance-runs/${run_id}" | jq -r '.execution_ref')"
  filter="$(temporal_cli workflow show --workflow-id "${execution_ref}" --output json \
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

progress "listing the namespaces of ${CATALOG} through the catalog API"
api GET "/v1/catalogs/${CATALOG}/namespaces" >/dev/null
catalog_round_trip

progress "issuing the Trino client certificate for ${TRINO_USER}"
task --dir "${ROOT}" trino:issue-cert \
  TRINO_USER="${TRINO_USER}" PRINT_USAGE=false KUBE_CONTEXT="${KUBE_CONTEXT}"

progress "ensuring the discovery rule ${CATALOG} / ${SCHEMA} / tm_e2e_*"
PRESET_ID="$(api GET /v1/table-maintenance-presets | jq -r '.[] | select(.name == "default") | .id')"
[[ -n "${PRESET_ID}" ]] || { echo "table maintenance preset default is missing" >&2; exit 1; }
RULE_ID="$(api GET /v1/table-discovery-rules | jq -r --arg ns "${SCHEMA}" \
  '.[] | select(.effect == "include" and .catalog_pattern == "iceberg"
    and .namespace_pattern == $ns and .table_pattern == "tm_e2e_*") | .id' | head -n 1)"
if [[ -z "${RULE_ID}" ]]; then
  RULE_ID="$(api POST /v1/table-discovery-rules "$(jq -cn --arg t "${PRESET_ID}" --arg ns "${SCHEMA}" \
    '{priority: 10, effect: "include", catalog_pattern: "iceberg", namespace_pattern: $ns,
      table_pattern: "tm_e2e_*", preset_id: $t, enabled: true}')" | jq -r '.id')"
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
  progress "table-reconciliation:table-uuid=${uuid} current run started at $(temporal_cli \
    workflow describe --workflow-id "table-reconciliation:table-uuid=${uuid}" --output json \
    | jq -r '.workflowExecutionInfo.startTime')"
done
progress "discovery schedule recent runs: $(temporal_cli schedule describe \
  --schedule-id "table-discovery:catalog=${CATALOG}" --output json \
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

progress "reading ${ORDERS} metadata, commits, health and storage through the API"
# shellcheck disable=SC2016
check 'any(.[]; .name == $t)' "$(api GET "/v1/catalogs/${CATALOG}/namespaces/${SCHEMA}/tables")" \
  "the table list of ${CATALOG}.${SCHEMA} lacks ${ORDERS}" --arg t "${ORDERS}"
ORDERS_METADATA="$(api GET "/v1/catalogs/${CATALOG}/namespaces/${SCHEMA}/tables/${ORDERS}")"
ORDERS_COMMITS="$(api GET "/v1/tables/${ORDERS_UUID}/commits?limit=1000")"
ORDERS_HEALTH="$(api GET "/v1/tables/${ORDERS_UUID}/health")"
ORDERS_STORAGE="$(api GET "/v1/tables/${ORDERS_UUID}/storage")"
jq -e '.uuid == "'"${ORDERS_UUID}"'"' <<<"${ORDERS_METADATA}" >/dev/null \
  || { echo "the catalog API returned another uuid than the maintenance table ${ORDERS_UUID}" >&2; exit 1; }
METADATA_FILES="$(jq '(.current_snapshot_id) as $current
  | ([.snapshots[] | select(.id == $current)][0].summary // {}) as $summary
  | (($summary["total-data-files"] // "0") | tonumber) + (($summary["total-delete-files"] // "0") | tonumber)' \
  <<<"${ORDERS_METADATA}")"
METADATA_SNAPSHOTS="$(jq '.snapshots | length' <<<"${ORDERS_METADATA}")"
progress "metadata: ${ORDERS} data+delete files=${METADATA_FILES} snapshots=${METADATA_SNAPSHOTS}"
(( METADATA_FILES == ORDERS_FILES_AFTER )) || {
  echo "metadata counts ${METADATA_FILES} data+delete files, \$files counts ${ORDERS_FILES_AFTER}" >&2
  exit 1
}
(( METADATA_SNAPSHOTS == ORDERS_SNAPSHOTS_AFTER )) || {
  echo "metadata counts ${METADATA_SNAPSHOTS} snapshots, \$snapshots counts ${ORDERS_SNAPSHOTS_AFTER}" >&2
  exit 1
}
jq -e '[.items[].committed_at | sub("\\.[0-9]+"; "") | sub("\\+00:00$"; "Z") | fromdateiso8601]
  | length > 0 and .[0] == max' <<<"${ORDERS_COMMITS}" >/dev/null \
  || { echo "${ORDERS} commits are not newest first" >&2; exit 1; }
jq -e '.operations | length == 4' <<<"${ORDERS_HEALTH}" >/dev/null \
  || { echo "${ORDERS} health does not report four operations" >&2; exit 1; }
RECLAIMED_REWRITTEN="$(jq '.reclaimed.rewritten_data_files // 0' <<<"${ORDERS_STORAGE}")"
progress "storage: ${ORDERS} reclaimed rewritten_data_files=${RECLAIMED_REWRITTEN}"
if (( RECLAIMED_REWRITTEN < 20 )); then
  if jq -e '[.[] | .operations[] | select(.operation == "rewrite_data_files")
      | .metrics.completed_without_callback] | any' <<<"${ORDERS_RUNS}" >/dev/null; then
    progress "${ORDERS}: the compaction callback was lost; skipping the reclaimed check"
  else
    echo "${ORDERS} storage reclaimed ${RECLAIMED_REWRITTEN} rewritten data files, expected >= 20" >&2
    exit 1
  fi
fi

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
