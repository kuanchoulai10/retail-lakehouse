#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
BACKEND_DIR="${REPO_ROOT}/src/data-platform/backend"
SPARK_DIR="${REPO_ROOT}/src/data-platform/runtime/spark"
CONSOLE_DIR="${REPO_ROOT}/src/console"

source_tag() {
  local source_dir="$1"
  local tag
  tag="$(git -C "${REPO_ROOT}" log -1 --format=%h -- "${source_dir}")"
  if [[ -z "${tag}" ]]; then
    echo "no commit touches ${source_dir}; commit the source before building" >&2
    return 1
  fi
  if [[ -n "$(git -C "${REPO_ROOT}" status --porcelain -- "${source_dir}")" ]]; then
    local content_hash
    content_hash="$(
      {
        git -C "${REPO_ROOT}" diff HEAD -- "${source_dir}"
        git -C "${REPO_ROOT}" ls-files --others --exclude-standard -z -- "${source_dir}" \
          | xargs -0 -I{} cat "${REPO_ROOT}/{}"
      } | shasum -a 256 | cut -c1-8
    )"
    tag="${tag}-dirty-${content_hash}"
  fi
  printf '%s' "${tag}"
}

build_and_load() {
  local name="$1"
  local source_dir="$2"
  local tag="$3"
  docker build \
    --tag "${name}:${tag}" \
    "${source_dir}" >&2
  minikube image load "${name}:${tag}" \
    --profile "${KUBE_CONTEXT}" >&2
}

BACKEND_TAG="$(source_tag "${BACKEND_DIR}")"
SPARK_TAG="$(source_tag "${SPARK_DIR}")"
CONSOLE_TAG="$(source_tag "${CONSOLE_DIR}")"

build_and_load table-maintenance-backend "${BACKEND_DIR}" "${BACKEND_TAG}"
build_and_load table-maintenance-spark "${SPARK_DIR}" "${SPARK_TAG}"
build_and_load console "${CONSOLE_DIR}" "${CONSOLE_TAG}"

printf 'BACKEND_TAG=%s\n' "${BACKEND_TAG}"
printf 'SPARK_TAG=%s\n' "${SPARK_TAG}"
printf 'CONSOLE_TAG=%s\n' "${CONSOLE_TAG}"
