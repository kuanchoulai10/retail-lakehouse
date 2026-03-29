#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

cd "$(dirname "$0")"

echo "==> Deleting Debezium MySQL connector (context: ${KUBE_CONTEXT})"

kubectl delete -f debezium-connector.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl delete -f debezium-connect-cluster.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl delete -f debezium-role-binding.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl delete -f debezium-role.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl delete -f debezium-secret.yaml -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
