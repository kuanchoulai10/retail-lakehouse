#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-1200s}"

log::on_success "Kafka cluster is ready"
log::on_failure "Kafka cluster is not ready"

kubectl wait kafka/kafka-cluster \
  --namespace kafka-cdc \
  --for=condition=Ready \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait pod \
  --selector app.kubernetes.io/name=entity-operator \
  --namespace kafka-cdc \
  --for=condition=Ready \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
