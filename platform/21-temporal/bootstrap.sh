#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/gateway.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TEMPORAL_CHART_VERSION="${TEMPORAL_CHART_VERSION:-1.7.0}"
TIMEOUT="${TIMEOUT:-600s}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Temporal chart ${TEMPORAL_CHART_VERSION} installed"
log::on_failure "Temporal installation failed"

helm repo add temporalio https://go.temporal.io/helm-charts --force-update
helm repo update temporalio

namespace::apply_ambient temporal

helm upgrade --install temporal temporalio/temporal \
  --version "${TEMPORAL_CHART_VERSION}" \
  --namespace temporal \
  --values "$SCRIPT_DIR/values.yaml" \
  --timeout "${TIMEOUT}" \
  --kube-context "${KUBE_CONTEXT}"

gateway::allow_routes temporal
kubectl apply \
  -f "$SCRIPT_DIR/temporal-web-route.yaml" \
  --context "${KUBE_CONTEXT}"

for deploy in temporal-frontend temporal-admintools; do
  kubectl rollout status "deployment/${deploy}" \
    --namespace temporal \
    --timeout "${TIMEOUT}" \
    --context "${KUBE_CONTEXT}"
done

temporal_cli() {
  kubectl exec deployment/temporal-admintools \
    --namespace temporal \
    --context "${KUBE_CONTEXT}" \
    -- temporal "$@"
}

SEARCH_ATTRIBUTES=""
for attempt in $(seq 1 30); do
  if SEARCH_ATTRIBUTES="$(temporal_cli operator search-attribute list --namespace default)"; then
    break
  fi
  if [[ "${attempt}" -eq 30 ]]; then
    echo "Temporal namespace default did not answer search-attribute list" >&2
    exit 1
  fi
  sleep 5
done

for attribute in TableUuid:Keyword TableName:Keyword MaintenanceOperations:KeywordList MaintenanceTrigger:Keyword GrantedTableUuids:KeywordList; do
  name="${attribute%%:*}"
  type="${attribute##*:}"
  if awk -v name="${name}" '$1 == name { found = 1 } END { exit !found }' <<<"${SEARCH_ATTRIBUTES}"; then
    echo "Search attribute ${name} already exists"
    continue
  fi
  temporal_cli operator search-attribute create --namespace default --name "${name}" --type "${type}"
done
