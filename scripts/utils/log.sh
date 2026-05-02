#!/usr/bin/env bash
# Shared leveled logging helpers.
#
#   log::debug "msg"   # [DEBUG] msg    (dim)
#   log::info  "msg"   #  [INFO] msg    (green)
#   log::warn  "msg"   #  [WARN] msg    (yellow)
#   log::error "msg"   # [ERROR] msg    (red, exits 1)
#
# Defer-until-exit mode (preferred for validate scripts):
#   log::on_success "Trino is ready"        # register success message
#   log::on_failure "Trino is broken"       # register failure message (optional)
#
# Either call lazily enables output buffering. On exit:
#   rc == 0 → print "[INFO] <success_msg>"  if registered, else silent
#   rc != 0 → print "[ERROR] <failure_msg>" if registered, then dump
#             captured stdout+stderr
#
# Honors NO_COLOR.

[[ -n "${__LOG_SH_LOADED:-}" ]] && return 0
__LOG_SH_LOADED=1

if [[ -z "${NO_COLOR:-}" ]]; then
  __LOG_RESET=$'\033[0m'
  __LOG_DIM=$'\033[2m'
  __LOG_RED=$'\033[31m'
  __LOG_GREEN=$'\033[32m'
  __LOG_YELLOW=$'\033[33m'
else
  __LOG_RESET='' __LOG_DIM=''
  __LOG_RED='' __LOG_GREEN='' __LOG_YELLOW=''
fi

log::debug() {
  printf '%s[DEBUG] %s%s\n' "$__LOG_DIM" "$1" "$__LOG_RESET"
}

log::info() {
  printf '%s [INFO] %s%s\n' "$__LOG_GREEN" "$1" "$__LOG_RESET"
}

log::warn() {
  printf '%s [WARN] %s%s\n' "$__LOG_YELLOW" "$1" "$__LOG_RESET"
}

log::error() {
  printf '%s[ERROR] %s%s\n' "$__LOG_RED" "$1" "$__LOG_RESET" >&2
  exit 1
}

log::on_success() {
  __LOG_SUCCESS_MSG="$1"
  __log::enable_buffering
}

log::on_failure() {
  __LOG_FAILURE_MSG="$1"
  __log::enable_buffering
}

__log::enable_buffering() {
  [[ -n "${__LOG_BUF:-}" ]] && return 0
  __LOG_BUF=$(mktemp)
  exec 3>&1 4>&2 >"$__LOG_BUF" 2>&1
  trap '__log::on_exit $?' EXIT
}

__log::on_exit() {
  local rc=$1
  exec 1>&3 2>&4 3>&- 4>&-
  if (( rc == 0 )); then
    [[ -n "${__LOG_SUCCESS_MSG:-}" ]] && log::info "$__LOG_SUCCESS_MSG"
  else
    [[ -n "${__LOG_FAILURE_MSG:-}" ]] && \
      printf '%s[ERROR] %s%s\n' "$__LOG_RED" "$__LOG_FAILURE_MSG" "$__LOG_RESET" >&2
    cat "$__LOG_BUF" >&2
  fi
  rm -f "$__LOG_BUF"
}
