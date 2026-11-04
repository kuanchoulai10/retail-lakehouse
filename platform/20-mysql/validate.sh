#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "MySQL is ready"
log::on_failure "MySQL is not ready"

namespace::assert_ambient ecommerce-app

kubectl rollout status deployment/mysql \
  --namespace ecommerce-app \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait pvc/mysql \
  --for=jsonpath='{.status.phase}'=Bound \
  --namespace ecommerce-app \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"
