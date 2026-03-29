#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Deploying Debezium MySQL connector (context: ${KUBE_CONTEXT})"

kubectl apply -f debezium-secret.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl apply -f debezium-role.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl apply -f debezium-role-binding.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl apply -f debezium-connect-cluster.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl apply -f debezium-connector.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
