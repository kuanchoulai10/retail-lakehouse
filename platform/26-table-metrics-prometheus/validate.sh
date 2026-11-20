#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

PROXY="/api/v1/namespaces/table-metrics/services/http:table-metrics-prometheus:9090/proxy"
SCRAPE_QUERY="up%7Bjob%3D%22table-maintenance-api%22%7D"
SCRAPE_WAIT_SECONDS=120

log::on_success "Table metrics Prometheus is ready"
log::on_failure "Table metrics Prometheus is not ready"

namespace::assert_ambient table-metrics

kubectl rollout status deployment/table-metrics-prometheus \
  --namespace table-metrics \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

scraped=""
deadline=$((SECONDS + SCRAPE_WAIT_SECONDS))
while [[ "${SECONDS}" -lt "${deadline}" ]]; do
  scraped="$(kubectl get --raw "${PROXY}/api/v1/query?query=${SCRAPE_QUERY}" \
    --context "${KUBE_CONTEXT}" \
    | yq -p json '.data.result[0].value[1]' || true)"
  [[ "${scraped}" == "1" ]] && break
  sleep 5
done
if [[ "${scraped}" != "1" ]]; then
  echo "up{job=\"table-maintenance-api\"} is '${scraped}', expected 1 within ${SCRAPE_WAIT_SECONDS}s" >&2
  exit 1
fi

retention="$(kubectl get --raw "${PROXY}/api/v1/status/flags" \
  --context "${KUBE_CONTEXT}" \
  | yq -p json '.data["storage.tsdb.retention.time"]')"
if [[ "${retention}" != "6h" ]]; then
  echo "storage.tsdb.retention.time is '${retention}', expected 6h" >&2
  exit 1
fi

mesh::assert_hbone table-metrics
