#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log::on_success "table-maintenance rewrite-data-files SparkApplication submitted"
log::on_failure "table-maintenance rewrite-data-files SparkApplication submission failed"

kubectl apply \
  -f "${SCRIPT_DIR}/sparkapplication-rewrite-data-files.yaml"
