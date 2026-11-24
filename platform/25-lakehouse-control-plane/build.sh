#!/usr/bin/env bash
set -euo pipefail

: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
BACKEND_DIR="${REPO_ROOT}/src/data-platform/backend"
SPARK_DIR="${REPO_ROOT}/src/data-platform/runtime/spark"
CONSOLE_DIR="${REPO_ROOT}/src/data-platform/frontend"
DESIGN_SYSTEM_DIR="${REPO_ROOT}/src/design-system"

source_tag() {
  local tag
  tag="$(git -C "${REPO_ROOT}" log -1 --format=%h -- "$@")"
  if [[ -z "${tag}" ]]; then
    echo "no commit touches $*; commit the source before building" >&2
    return 1
  fi
  if [[ -n "$(git -C "${REPO_ROOT}" status --porcelain -- "$@")" ]]; then
    local content_hash
    content_hash="$(
      {
        git -C "${REPO_ROOT}" diff HEAD -- "$@"
        git -C "${REPO_ROOT}" ls-files --others --exclude-standard -z -- "$@" \
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
  shift 3
  docker build \
    --tag "${name}:${tag}" \
    "$@" \
    "${source_dir}" >&2
  load_image "${name}" "${tag}"
}

load_image() {
  local name="$1"
  local tag="$2"
  if minikube image ls --profile "${KUBE_CONTEXT}" | grep -qxF "docker.io/library/${name}:${tag}"; then
    echo "${name}:${tag} is already on the node" >&2
    return 0
  fi
  minikube image load "${name}:${tag}" \
    --profile "${KUBE_CONTEXT}" >&2
}

E2E_SOURCES=(
  "${BACKEND_DIR}/e2e"
  "${BACKEND_DIR}/e2e.Dockerfile"
  "${BACKEND_DIR}/requirements-e2e.txt"
)
BACKEND_TAG="$(source_tag "${BACKEND_DIR}" "${E2E_SOURCES[@]/#/:(exclude)}")"
E2E_TAG="$(source_tag "${BACKEND_DIR}")"
SPARK_TAG="$(source_tag "${SPARK_DIR}")"
CONSOLE_SOURCES=(
  "${CONSOLE_DIR}"
  "${DESIGN_SYSTEM_DIR}"
  "${REPO_ROOT}/package.json"
  "${REPO_ROOT}/package-lock.json"
)
CONSOLE_TAG="$(source_tag "${CONSOLE_SOURCES[@]}")"

build_and_load table-maintenance-backend "${BACKEND_DIR}" "${BACKEND_TAG}"
build_and_load table-maintenance-spark "${SPARK_DIR}" "${SPARK_TAG}"
build_and_load console "${REPO_ROOT}" "${CONSOLE_TAG}" --file "${CONSOLE_DIR}/Dockerfile"
E2E_CONTEXT="$(mktemp -d)"
trap 'rm -r -f "${E2E_CONTEXT}"' EXIT
rsync -a --exclude '__pycache__' --exclude '*.pyc' \
  "${BACKEND_DIR}/e2e.Dockerfile" "${BACKEND_DIR}/requirements-e2e.txt" "${BACKEND_DIR}/e2e" \
  "${E2E_CONTEXT}/"
build_and_load table-maintenance-e2e "${E2E_CONTEXT}" "${E2E_TAG}" \
  --file "${E2E_CONTEXT}/e2e.Dockerfile" \
  --build-arg "BACKEND_IMAGE=table-maintenance-backend:${BACKEND_TAG}"

printf 'BACKEND_TAG=%s\n' "${BACKEND_TAG}"
printf 'SPARK_TAG=%s\n' "${SPARK_TAG}"
printf 'CONSOLE_TAG=%s\n' "${CONSOLE_TAG}"
printf 'E2E_TAG=%s\n' "${E2E_TAG}"
