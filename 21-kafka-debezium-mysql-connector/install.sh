#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-mini}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying Debezium MySQL connector (context: ${KUBE_CONTEXT})"

kubectl apply -f "$SCRIPT_DIR/debezium-secret.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/debezium-role.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/debezium-role-binding.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/debezium-connect-cluster.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"
kubectl apply -f "$SCRIPT_DIR/debezium-connector.yaml" -n kafka-cdc --context "${KUBE_CONTEXT}"

echo "==> Done."
