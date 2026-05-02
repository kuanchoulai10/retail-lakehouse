#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-1200s}"

echo "==> Validating Debezium MySQL connector (context: ${KUBE_CONTEXT})"

kubectl wait kafkaconnect/debezium-connect-cluster \
  -n kafka-cdc \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait kafkaconnector/debezium-connector \
  -n kafka-cdc \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

echo "==> Debezium connector is ready."
