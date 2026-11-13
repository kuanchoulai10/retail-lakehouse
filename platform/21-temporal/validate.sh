#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/gateway.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Temporal is ready"
log::on_failure "Temporal is not ready"

namespace::assert_ambient temporal

for deploy in temporal-frontend temporal-history temporal-matching temporal-worker temporal-web temporal-admintools; do
  kubectl rollout status "deployment/${deploy}" \
    --namespace temporal \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
done

HEALTH="$(kubectl exec deployment/temporal-admintools \
  --namespace temporal \
  --context "${KUBE_CONTEXT}" \
  -- temporal operator cluster health)"
echo "${HEALTH}"
grep -q SERVING <<<"${HEALTH}"

kubectl exec deployment/temporal-admintools \
  --namespace temporal \
  --context "${KUBE_CONTEXT}" \
  -- temporal operator namespace describe -n default

SEARCH_ATTRIBUTES="$(kubectl exec deployment/temporal-admintools \
  --namespace temporal \
  --context "${KUBE_CONTEXT}" \
  -- temporal operator search-attribute list --namespace default)"
for attribute in TableUuid:Keyword TableName:Keyword MaintenanceOperations:KeywordList MaintenanceTrigger:Keyword GrantedTableUuids:KeywordList; do
  name="${attribute%%:*}"
  type="${attribute##*:}"
  if ! awk -v name="${name}" -v type="${type}" '$1 == name && $2 == type { found = 1 } END { exit !found }' <<<"${SEARCH_ATTRIBUTES}"; then
    echo "Search attribute ${name} of type ${type} is missing from Temporal namespace default" >&2
    exit 1
  fi
done

gateway::assert_routes_allowed temporal
gateway::assert_route_accepted temporal temporal-web
gateway::curl /temporal/ -fsS -o /dev/null
