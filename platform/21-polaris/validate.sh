#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Polaris is ready"
log::on_failure "Polaris is not ready"

kubectl get secret polaris-token-broker \
  --namespace lakehouse-catalog \
  --context "${KUBE_CONTEXT}" >/dev/null

kubectl rollout status deployment/polaris \
  --namespace lakehouse-catalog \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait \
  --for=condition=complete job/polaris-create-catalog \
  --namespace lakehouse-catalog \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait kafkatopic/polaris-catalog-events \
  --for=condition=Ready \
  --timeout "${TIMEOUT}" \
  --namespace kafka \
  --context "${KUBE_CONTEXT}"
