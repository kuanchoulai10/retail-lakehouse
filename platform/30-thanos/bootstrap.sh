#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log::on_success "Thanos installed"
log::on_failure "Thanos installation failed"

kubectl create namespace thanos \
  --context "${KUBE_CONTEXT}" || true

# Render manifests using kube-thanos jsonnet
# https://github.com/thanos-io/kube-thanos
jb install github.com/thanos-io/kube-thanos/jsonnet/kube-thanos@main
rm -f "$SCRIPT_DIR/manifests/"thanos-*
jsonnet -J "$SCRIPT_DIR/vendor" -m "$SCRIPT_DIR/manifests/" "$SCRIPT_DIR/thanos.jsonnet" | xargs -I{} sh -c "cat {} | yq -P > {}.yaml; rm -f {}" -- {}

kubectl apply \
  -f "$SCRIPT_DIR/manifests/" \
  --context "${KUBE_CONTEXT}"
