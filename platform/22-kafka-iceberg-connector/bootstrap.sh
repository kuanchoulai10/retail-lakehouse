#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Iceberg sink connector deployed"
log::on_failure "Iceberg sink connector deployment failed"

kubectl apply \
  -f "$SCRIPT_DIR/iceberg-secret.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"

# Resolve current minikube registry ClusterIP and render the KafkaConnect
# manifest. The build.output.image must be an IP because image pull happens
# at kubelet/containerd level using node DNS, which can't resolve cluster
# service names. The IP changes on every minikube rebuild.
REGISTRY_IP="$(kubectl get svc registry \
  --namespace kube-system \
  --output jsonpath='{.spec.clusterIP}' \
  --context "${KUBE_CONTEXT}")"
export REGISTRY_IP

# shellcheck disable=SC2016 # envsubst takes literal '${VAR}' to restrict substitution
envsubst '${REGISTRY_IP}' < "$SCRIPT_DIR/iceberg-connect-cluster.yaml" \
  | kubectl apply \
    -f - \
    --namespace kafka-cdc \
    --context "${KUBE_CONTEXT}"
kubectl apply \
  -f "$SCRIPT_DIR/iceberg-connector.yaml" \
  --namespace kafka-cdc \
  --context "${KUBE_CONTEXT}"
