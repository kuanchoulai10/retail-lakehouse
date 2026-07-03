#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Debezium Polaris connector deployed"
log::on_failure "Debezium Polaris connector deployment failed"

POLARIS_DB_POD=$(kubectl get pod \
  --selector app=polaris-db \
  --namespace polaris \
  --output jsonpath='{.items[0].metadata.name}' \
  --context "${KUBE_CONTEXT}")

kubectl exec "$POLARIS_DB_POD" \
  --namespace polaris \
  --context "${KUBE_CONTEXT}" \
  -- psql -U polaris -d polaris -tAc \
    "SELECT 1 FROM pg_publication WHERE pubname = 'polaris_cdc'" \
  | grep -q 1 \
  || kubectl exec "$POLARIS_DB_POD" \
       --namespace polaris \
       --context "${KUBE_CONTEXT}" \
       -- psql -U polaris -d polaris -c \
         "CREATE PUBLICATION polaris_cdc FOR TABLE polaris_schema.commit_metrics_report;"

kubectl apply \
  -f "$SCRIPT_DIR/debezium-secret.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/debezium-role.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/debezium-role-binding.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"

REGISTRY_IP="$(kubectl get svc registry \
  --namespace kube-system \
  --output jsonpath='{.spec.clusterIP}' \
  --context "${KUBE_CONTEXT}")"
export REGISTRY_IP

# shellcheck disable=SC2016
envsubst '${REGISTRY_IP}' < "$SCRIPT_DIR/debezium-connect-cluster.yaml" \
  | kubectl apply \
    -f - \
    --namespace kafka-cdc \
    --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/debezium-connector.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"
