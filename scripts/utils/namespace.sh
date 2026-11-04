#!/usr/bin/env bash
# shellcheck disable=SC2154
# Ambient mesh namespace helpers. Every function reads KUBE_CONTEXT.
#
#   namespace::apply_ambient <name>   # create-or-update the namespace labelled ambient
#   namespace::assert_ambient <name>  # fail unless istio.io/dataplane-mode=ambient
#   mesh::assert_hbone <namespace>    # fail unless every Running pod is HBONE in ztunnel

[[ -n "${__NAMESPACE_SH_LOADED:-}" ]] && return 0
__NAMESPACE_SH_LOADED=1

namespace::apply_ambient() {
  local name=$1
  kubectl apply --server-side \
    --field-manager namespace-ambient \
    -f - \
    --context "${KUBE_CONTEXT}" <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: ${name}
  labels:
    istio.io/dataplane-mode: ambient
EOF
}

namespace::assert_ambient() {
  local name=$1 value
  value=$(kubectl get namespace "$name" \
    -o jsonpath='{.metadata.labels.istio\.io/dataplane-mode}' \
    --context "${KUBE_CONTEXT}")
  if [[ "$value" != "ambient" ]]; then
    echo "namespace $name is missing label istio.io/dataplane-mode=ambient (found '${value}')" >&2
    return 1
  fi
}

__mesh::fetch_workloads() {
  local ztunnel=$1 pf_pid pf_log port=""
  pf_log=$(mktemp)
  kubectl port-forward "pod/${ztunnel}" :15000 \
    --namespace istio-system \
    --context "${KUBE_CONTEXT}" >"$pf_log" 2>&1 &
  pf_pid=$!
  # shellcheck disable=SC2064
  trap "kill $pf_pid 2>/dev/null || true; wait $pf_pid 2>/dev/null || true; rm -f '$pf_log'; trap - RETURN" RETURN
  for _ in $(seq 1 50); do
    port=$(sed -n 's/^Forwarding from 127\.0\.0\.1:\([0-9]*\) ->.*/\1/p' "$pf_log" | head -n 1)
    [[ -n "$port" ]] && break
    kill -0 "$pf_pid" 2>/dev/null || break
    sleep 0.1
  done
  if [[ -z "$port" ]]; then
    echo "port-forward to ${ztunnel} did not start" >&2
    cat "$pf_log" >&2
    return 1
  fi
  curl -sf --max-time 5 "http://127.0.0.1:${port}/config_dump" || return 1
}

mesh::assert_hbone() {
  local namespace=$1 node pod n ztunnel dump rc=0 pods
  pods=$(kubectl get pods \
    --field-selector status.phase=Running \
    -o jsonpath='{range .items[*]}{.spec.nodeName}{" "}{.metadata.name}{"\n"}{end}' \
    --namespace "$namespace" \
    --context "${KUBE_CONTEXT}")
  if [[ -z "$pods" ]]; then
    echo "no Running pods in namespace $namespace" >&2
    return 1
  fi
  while read -r node; do
    ztunnel=$(kubectl get pods \
      -l app=ztunnel \
      --field-selector "spec.nodeName=${node}" \
      -o jsonpath='{.items[*].metadata.name}' \
      --namespace istio-system \
      --context "${KUBE_CONTEXT}")
    ztunnel=${ztunnel%% *}
    if [[ -z "$ztunnel" ]]; then
      echo "no ztunnel pod on node $node" >&2
      return 1
    fi
    dump=$(__mesh::fetch_workloads "$ztunnel") || return 1
    while read -r n pod; do
      [[ "$n" == "$node" ]] || continue
      if ! jq -e --arg ns "$namespace" --arg name "$pod" '
          .workloads
          | (if type == "object" then [.[]] else . end)
          | any(.[]; .namespace == $ns and .name == $name and .protocol == "HBONE")' \
          <<<"$dump" >/dev/null; then
        echo "pod $namespace/$pod is not HBONE in ztunnel $ztunnel" >&2
        rc=1
      else
        echo "pod $namespace/$pod is HBONE"
      fi
    done <<<"$pods"
  done < <(awk '{print $1}' <<<"$pods" | sort -u)
  return "$rc"
}
