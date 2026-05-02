#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"

echo "==> Uninstalling Apache Polaris (context: ${KUBE_CONTEXT})"

helm uninstall polaris \
  --namespace polaris \
  --kube-context "${KUBE_CONTEXT}"

echo "==> Done."
