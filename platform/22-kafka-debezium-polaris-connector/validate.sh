#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-1200s}"

log::on_success "Debezium Polaris connector is ready"
log::on_failure "Debezium Polaris connector is not ready"

kubectl wait kafkaconnect/polaris-cdc-connect-cluster \
  --namespace kafka-cdc \
  --for=condition=Ready \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait kafkaconnector/polaris-cdc-connector \
  --namespace kafka-cdc \
  --for=condition=Ready \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
