#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_FILE="vast-balance.service"
SERVICE_USER="vast-revenue-monitor"
APP_DIR="/opt/vast-revenue-monitor"
UNIT_PATH="/etc/systemd/system/${SERVICE_FILE}"
PURGE=false
ASSUME_YES=false

log() {
  printf '[vast-revenue-monitor] %s\n' "$*"
}

fail() {
  printf '[vast-revenue-monitor] ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: sudo bash uninstall.sh [--purge] [--yes]

Without --purge, the service is removed but /opt/vast-revenue-monitor is kept.
  --purge  Also permanently delete config, state, logs, code, and service account.
  --yes    Skip the PURGE confirmation; valid only together with --purge.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --purge) PURGE=true ;;
    --yes) ASSUME_YES=true ;;
    --help|-h) usage; exit 0 ;;
    *) usage; fail "unknown argument: $1" ;;
  esac
  shift
done

[[ "${EUID}" -eq 0 ]] || fail "Run as root: sudo bash uninstall.sh"
if [[ "${ASSUME_YES}" == true && "${PURGE}" != true ]]; then
  fail "--yes may only be used with --purge"
fi

if [[ "${PURGE}" == true && "${ASSUME_YES}" != true ]]; then
  [[ -t 0 ]] || fail "Use --purge --yes for non-interactive removal"
  printf 'This permanently deletes %s, including config and history.\n' "${APP_DIR}"
  read -r -p 'Type PURGE to continue: ' confirmation
  [[ "${confirmation}" == "PURGE" ]] || fail "purge cancelled"
fi

log "Stopping and disabling ${SERVICE_FILE}..."
systemctl stop "${SERVICE_FILE}" 2>/dev/null || true
systemctl disable "${SERVICE_FILE}" 2>/dev/null || true
rm -f -- "${UNIT_PATH}"
systemctl daemon-reload
systemctl reset-failed "${SERVICE_FILE}" 2>/dev/null || true

if [[ "${PURGE}" == true ]]; then
  log "Permanently removing application data and service account..."
  rm -rf -- "${APP_DIR}"
  rm -rf -- /opt/.vast-revenue-monitor.new.* /opt/.vast-revenue-monitor.old.*
  rm -f -- /tmp/vast-revenue-monitor-api_response.json
  if id -u "${SERVICE_USER}" >/dev/null 2>&1; then
    userdel "${SERVICE_USER}"
  fi
  if getent group "${SERVICE_USER}" >/dev/null 2>&1; then
    groupdel "${SERVICE_USER}"
  fi
  log "Purge completed. The next install will be treated as a new installation."
else
  log "Service removed; ${APP_DIR} was preserved."
  log "Run with --purge to delete config, state, logs, and the service account."
fi
