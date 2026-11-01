#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"

log::on_success "Kafbat UI is ready"
log::on_failure "Kafbat UI is not ready"

namespace::assert_ambient kafka-ui

kubectl rollout status deployment/kafka-ui \
  --namespace kafka-ui \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

mesh::assert_hbone kafka-ui
