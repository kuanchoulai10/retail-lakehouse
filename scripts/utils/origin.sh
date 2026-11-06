#!/usr/bin/env bash
# Public origin of the platform gateway (the URL browsers use to reach the UIs).
#
#   origin::public    # print the origin without a trailing slash, or fail
#
# PUBLIC_ORIGIN, when set and non-empty, wins. Otherwise the origin is
# https://<tailscale DNS name>:8591 taken from `tailscale status --json`.

[[ -n "${__ORIGIN_SH_LOADED:-}" ]] && return 0
__ORIGIN_SH_LOADED=1

ORIGIN_TAILSCALE_PORT=8591

origin::public() {
  local name=""
  if [[ -n "${PUBLIC_ORIGIN:-}" ]]; then
    printf '%s\n' "${PUBLIC_ORIGIN%/}"
    return 0
  fi
  if command -v tailscale >/dev/null 2>&1; then
    name=$(tailscale status --json 2>/dev/null | jq -r '.Self.DNSName // empty' 2>/dev/null || true)
    name=${name%.}
    name=$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')
  fi
  if [[ -z "$name" ]]; then
    echo "public origin unknown: set PUBLIC_ORIGIN or run tailscale" >&2
    return 1
  fi
  printf 'https://%s:%s\n' "$name" "$ORIGIN_TAILSCALE_PORT"
}
