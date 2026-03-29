#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"
TIMEOUT="${TIMEOUT:-1200s}"

echo "==> Validating Iceberg sink connector (context: ${KUBE_CONTEXT})"

kubectl wait pod \
  -l app.kubernetes.io/name=kafka-connect \
  -l app.kubernetes.io/instance=iceberg-connect-cluster \
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
