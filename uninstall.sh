#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_FILE="vast-balance.service"
SERVICE_USER="vast-revenue-monitor"
APP_DIR="/opt/vast-revenue-monitor"
UNIT_PATH="/etc/systemd/system/${SERVICE_FILE}"
PURGE="ask"
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

Without --purge, you are asked whether logs and history should be deleted.
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

if [[ "${PURGE}" == "ask" ]]; then
  [[ -t 0 ]] || fail "Use --purge --yes for non-interactive removal"
  printf 'This will completely remove Vast Revenue Monitor.\n'
  read -r -p 'Delete all logs and history? [Y/n] ' confirmation
  if [[ "${confirmation:-Y}" =~ ^[Yy]$ ]]; then PURGE=true; else PURGE=false; fi
elif [[ "${PURGE}" == true && "${ASSUME_YES}" != true ]]; then
  read -r -p 'Delete all logs and history? [Y/n] ' confirmation
  [[ "${confirmation:-Y}" =~ ^[Yy]$ ]] || PURGE=false
fi

log "Stopping and disabling ${SERVICE_FILE}..."
systemctl stop "${SERVICE_FILE}" 2>/dev/null || true
systemctl disable "${SERVICE_FILE}" 2>/dev/null || true
rm -f -- "${UNIT_PATH}"
rm -f -- /etc/cron.d/vast-revenue-monitor
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
  log "Removing runtime while preserving config and history..."
  PRESERVE_DIR="$(mktemp -d /tmp/vast-revenue-preserve.XXXXXX)"
  [[ ! -f "${APP_DIR}/config.json" ]] || cp -a "${APP_DIR}/config.json" "${PRESERVE_DIR}/"
  [[ ! -d "${APP_DIR}/state" ]] || cp -a "${APP_DIR}/state" "${PRESERVE_DIR}/"
  rm -rf -- "${APP_DIR}"
  install -d -m 0755 "${APP_DIR}"
  cp -a "${PRESERVE_DIR}/." "${APP_DIR}/"
  rm -rf "${PRESERVE_DIR}"
  log "Service removed; config and state history were preserved in ${APP_DIR}."
fi
