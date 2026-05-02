#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-1200s}"

echo "==> Validating Iceberg sink connector (context: ${KUBE_CONTEXT})"

kubectl wait kafkaconnect/iceberg-connect-cluster \
  -n kafka-cdc \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait kafkaconnector/iceberg-connector \
  -n kafka-cdc \
  --for=condition=Ready \
  --timeout="${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

echo "==> Iceberg connector is ready."
