#!/usr/bin/env bash
# Shared logging helpers for cluster install/validate/uninstall scripts.
#
# Quiet mode (preferred for validate scripts):
#   log::quiet "Trino is ready"   # buffer all output; on success print "✓ ...",
#                                 # on failure dump captured stdout+stderr.
#
# Verbose helpers (output goes to the active sink — stdout, or buffer under quiet):
#   log::header "Validating Trino"        # ▸ Validating Trino (context: ...)
#   log::step   "Checking JMX sidecar"    #   ▸ Checking JMX sidecar
#   log::ok     "JMX sidecar found"       #   ✓ JMX sidecar found
#   log::detail "Found 2 healthy targets" #     Found 2 healthy targets
#   log::warn   "Stale image detected"    #   ⚠ Stale image detected
#   log::fail   "Expected 401, got 500"   #   ✗ Expected 401, got 500    (exits 1)
#   log::footer "Trino is ready"          # ✓ Trino is ready
#
# Honors NO_COLOR. Reads KUBE_CONTEXT for the header context tag (optional).

[[ -n "${__LOG_SH_LOADED:-}" ]] && return 0
__LOG_SH_LOADED=1

if [[ -z "${NO_COLOR:-}" ]]; then
  __LOG_RESET=$'\033[0m'
  __LOG_BOLD=$'\033[1m'
  __LOG_DIM=$'\033[2m'
  __LOG_RED=$'\033[31m'
  __LOG_GREEN=$'\033[32m'
  __LOG_YELLOW=$'\033[33m'
  __LOG_CYAN=$'\033[36m'
else
  __LOG_RESET='' __LOG_BOLD='' __LOG_DIM=''
  __LOG_RED='' __LOG_GREEN='' __LOG_YELLOW='' __LOG_CYAN=''
fi

log::header() {
  local title="$1"
  if [[ -n "${KUBE_CONTEXT:-}" ]]; then
    printf '%s▸%s %s%s%s %s(context: %s)%s\n' \
      "$__LOG_CYAN" "$__LOG_RESET" \
      "$__LOG_BOLD" "$title" "$__LOG_RESET" \
      "$__LOG_DIM" "$KUBE_CONTEXT" "$__LOG_RESET"
  else
    printf '%s▸%s %s%s%s\n' \
      "$__LOG_CYAN" "$__LOG_RESET" \
      "$__LOG_BOLD" "$title" "$__LOG_RESET"
  fi
}

log::step() {
  printf '  %s▸%s %s\n' "$__LOG_CYAN" "$__LOG_RESET" "$1"
}

log::ok() {
  printf '  %s✓%s %s\n' "$__LOG_GREEN" "$__LOG_RESET" "$1"
}

log::detail() {
  printf '    %s%s%s\n' "$__LOG_DIM" "$1" "$__LOG_RESET"
}

log::warn() {
  printf '  %s⚠%s %s\n' "$__LOG_YELLOW" "$__LOG_RESET" "$1"
}

log::fail() {
  printf '  %s✗ %s%s\n' "$__LOG_RED" "$1" "$__LOG_RESET" >&2
  exit 1
}

log::footer() {
  printf '%s✓%s %s\n' "$__LOG_GREEN" "$__LOG_RESET" "$1"
}

log::quiet() {
  __LOG_FOOTER="${1:-done}"
  __LOG_BUF=$(mktemp)
  exec 3>&1 4>&2 >"$__LOG_BUF" 2>&1
  trap '__log::on_exit $?' EXIT
}

__log::on_exit() {
  local rc=$1
  exec 1>&3 2>&4 3>&- 4>&-
  if (( rc == 0 )); then
    log::footer "$__LOG_FOOTER"
  else
    cat "$__LOG_BUF" >&2
  fi
  rm -f "$__LOG_BUF"
}
