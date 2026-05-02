#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::header "Validating KEDA"

kubectl rollout status deployment/keda-operator \
  -n keda --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/keda-operator-metrics-apiserver \
  -n keda --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"
kubectl rollout status deployment/keda-admission-webhooks \
  -n keda --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

log::footer "KEDA is ready"
