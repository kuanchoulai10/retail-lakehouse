#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "MySQL deployed"
log::on_failure "MySQL deployment failed"

namespace::apply_ambient ecommerce-app

kubectl apply \
  -f "$SCRIPT_DIR/mysql-secret.yaml" \
  --context "${KUBE_CONTEXT}"

kubectl apply \
  -f "$SCRIPT_DIR/mysql.yaml" \
  --namespace ecommerce-app \
  --context "${KUBE_CONTEXT}"
