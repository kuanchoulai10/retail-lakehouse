#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-retail-lakehouse}"
TIMEOUT="${TIMEOUT:-300s}"

echo "==> Validating Trino (context: ${KUBE_CONTEXT})"

kubectl wait --for=condition=Ready certificate/trino-tls \
  -n trino --timeout=60s --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/trino-coordinator \
  -n trino --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

kubectl rollout status deployment/trino-worker \
  -n trino --timeout="${TIMEOUT}" --context "${KUBE_CONTEXT}"

echo "==> Validating JMX exporter sidecar is running"
CONTAINERS=$(kubectl get deployment/trino-coordinator -n trino --context "${KUBE_CONTEXT}" \
  -o jsonpath='{.spec.template.spec.containers[*].name}' | wc -w | tr -d ' ')
if [ "${CONTAINERS}" -lt 2 ]; then
  echo "ERROR: JMX exporter sidecar not found in coordinator (expected 2 containers)"
  exit 1
fi

echo "==> Validating ServiceMonitor exists"
kubectl get servicemonitor trino -n trino --context "${KUBE_CONTEXT}" > /dev/null
kubectl get servicemonitor trino-worker -n trino --context "${KUBE_CONTEXT}" > /dev/null

echo "==> Validating Prometheus RBAC for trino namespace"
kubectl auth can-i list services \
  --as=system:serviceaccount:monitoring:prometheus-k8s \
  -n trino --context "${KUBE_CONTEXT}" | grep -q "^yes$"

echo "==> Validating Prometheus is scraping Trino targets"
TRINO_TARGETS=$(kubectl exec -n monitoring prometheus-k8s-0 --context "${KUBE_CONTEXT}" -- \
  wget -qO- 'http://localhost:9090/api/v1/targets' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
up = [t for t in data['data']['activeTargets']
      if 'trino' in t.get('scrapePool','') and t.get('health') == 'up']
print(len(up))
")
if [ "${TRINO_TARGETS}" -lt 1 ]; then
  echo "ERROR: No healthy Trino targets found in Prometheus"
  exit 1
fi
echo "  Found ${TRINO_TARGETS} healthy Trino target(s)"

echo "==> Validating mTLS truststore exists in coordinator"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  test -s /etc/trino/truststore/truststore.p12

echo "==> Validating authentication.type includes certificate"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  grep -q '^http-server.authentication.type=certificate,oauth2$' /etc/trino/config.properties

echo "==> Validating user-mapping pattern set"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  grep -q '^http-server.authentication.certificate.user-mapping.pattern=' /etc/trino/config.properties

echo "==> Validating truststore path set"
kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  grep -q '^http-server.https.truststore.path=' /etc/trino/config.properties

echo "==> Validating server rejects unauthenticated HTTPS request"
STATUS=$(kubectl exec -n trino deployment/trino-coordinator --context "${KUBE_CONTEXT}" -- \
  curl -sk -o /dev/null -w "%{http_code}" https://localhost:8443/v1/statement -X POST -d 'SELECT 1')
case "$STATUS" in
  401|403) echo "  Server rejected unauth request with HTTP $STATUS (expected)";;
  *) echo "ERROR: expected 401/403, got $STATUS"; exit 1;;
esac

echo "==> Trino is ready."
