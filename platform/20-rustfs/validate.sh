#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/log.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/utils/namespace.sh"

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"
TIMEOUT="${TIMEOUT:-300s}"
S3API_TIMEOUT="${S3API_TIMEOUT:-180s}"

AWS_CLI_IMAGE="amazon/aws-cli:2.38.1"
EVENT_LOG_BUCKET="spark-event-logs"
EVENT_LOG_TARGET_ARN="arn:rustfs:sqs:us-east-1:spark_event_logs:kafka"

log::on_success "RustFS is ready"
log::on_failure "RustFS is not ready"

namespace::assert_ambient object-storage

kubectl rollout status deployment/rustfs \
  --namespace object-storage \
  --timeout "${TIMEOUT}" \
  --context "${KUBE_CONTEXT}"

kubectl wait job/rustfs-create-bucket \
  --for=condition=complete \
  --timeout "${TIMEOUT}" \
  --namespace object-storage \
  --context "${KUBE_CONTEXT}"

kubectl wait kafkatopic/spark-event-log-completions \
  --for=condition=Ready \
  --timeout "${TIMEOUT}" \
  --namespace kafka \
  --context "${KUBE_CONTEXT}"

timestamp_type="$(kubectl get kafkatopic/spark-event-log-completions \
  -o jsonpath='{.spec.config.message\.timestamp\.type}' \
  --namespace kafka \
  --context "${KUBE_CONTEXT}")"
if [[ "${timestamp_type}" != "LogAppendTime" ]]; then
  log::error "Topic spark-event-log-completions must use LogAppendTime (found '${timestamp_type}')"
fi

s3api() {
  local pod args overrides rc=0
  args="$(printf '%s\n' "$@" | jq -R . | jq -cs .)"
  pod="rustfs-validate-$(date +%s)-${RANDOM}"
  overrides="$(jq -cn --arg image "${AWS_CLI_IMAGE}" --argjson args "${args}" '{spec: {containers: [{
    name: "aws", image: $image,
    envFrom: [{secretRef: {name: "rustfs-secret"}}],
    command: (["sh", "-ec",
      "AWS_ACCESS_KEY_ID=\"$RUSTFS_ACCESS_KEY\" AWS_SECRET_ACCESS_KEY=\"$RUSTFS_SECRET_KEY\" exec aws \"$@\"",
      "aws", "--endpoint-url", "http://rustfs.object-storage.svc.cluster.local:9000",
      "--region", "us-east-1", "--output", "json", "s3api"] + $args)}]}}')"
  kubectl run "${pod}" \
    --restart Never \
    --image "${AWS_CLI_IMAGE}" \
    --overrides "${overrides}" \
    --namespace object-storage \
    --context "${KUBE_CONTEXT}" >/dev/null
  kubectl wait "pod/${pod}" \
    --for=jsonpath='{.status.phase}'=Succeeded \
    --timeout "${S3API_TIMEOUT}" \
    --namespace object-storage \
    --context "${KUBE_CONTEXT}" >/dev/null || rc=$?
  kubectl logs "pod/${pod}" \
    --namespace object-storage \
    --context "${KUBE_CONTEXT}" || rc=$?
  kubectl delete "pod/${pod}" \
    --ignore-not-found \
    --wait=false \
    --namespace object-storage \
    --context "${KUBE_CONTEXT}" >/dev/null || true
  return "${rc}"
}

s3api head-bucket --bucket "${EVENT_LOG_BUCKET}"

lifecycle="$(s3api get-bucket-lifecycle-configuration --bucket "${EVENT_LOG_BUCKET}")"
if ! jq -e '[.Rules[] | select(.Status == "Enabled" and .Expiration.Days == 3)] | length >= 1' \
  <<<"${lifecycle}" >/dev/null; then
  log::error "Bucket ${EVENT_LOG_BUCKET} has no enabled 3-day expiry rule: ${lifecycle}"
fi

notification="$(s3api get-bucket-notification-configuration --bucket "${EVENT_LOG_BUCKET}")"
if ! jq -e --arg arn "${EVENT_LOG_TARGET_ARN}" \
  '[.QueueConfigurations[]? | select(.QueueArn == $arn)] | length >= 1' \
  <<<"${notification}" >/dev/null; then
  log::error "Bucket ${EVENT_LOG_BUCKET} has no notification for ${EVENT_LOG_TARGET_ARN}: ${notification}"
fi
