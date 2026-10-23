#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Temporal is ready"
log::on_failure "Temporal is not ready"

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
  -- temporal operator namespace describe default
