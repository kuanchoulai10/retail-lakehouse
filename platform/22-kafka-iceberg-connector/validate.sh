#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-1200s}"

log::on_success "Iceberg connector is ready"
log::on_failure "Iceberg connector is not ready"

kubectl wait kafkaconnect/iceberg-connect-cluster \
  --namespace kafka-cdc \
  --for=condition=Ready \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait kafkaconnector/iceberg-connector \
  --namespace kafka-cdc \
  --for=condition=Ready \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
