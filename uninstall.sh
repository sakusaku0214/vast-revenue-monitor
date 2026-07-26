#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_FILE="vast-balance.service"
SERVICE_USER="vast-revenue-monitor"
APP_DIR="/opt/vast-revenue-monitor"
UNIT_PATH="/etc/systemd/system/${SERVICE_FILE}"
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
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
  if [[ "${confirmation:-Y}" =~ ^[Yy]$ ]]; then
    PURGE=true
  else
    PURGE=backup
  fi
elif [[ "${PURGE}" == true && "${ASSUME_YES}" != true ]]; then
  read -r -p 'Delete all logs and history? [Y/n] ' confirmation
  [[ "${confirmation:-Y}" =~ ^[Yy]$ ]] || PURGE=backup
fi

if [[ "${PURGE}" == backup ]]; then
  [[ -f "${APP_DIR}/config.json" && -d "${APP_DIR}/state" ]] || \
    fail "config/state not found; cannot create preservation backup"
  BACKUP_FILE="${PWD}/vast-revenue-monitor-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
  log "Creating preservation backup before complete removal..."
  tar -czf "${BACKUP_FILE}" -C "${APP_DIR}" config.json state
  chmod 600 "${BACKUP_FILE}"
  if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != root ]]; then
    chown "${SUDO_USER}" "${BACKUP_FILE}"
  fi
  [[ -s "${BACKUP_FILE}" ]] || fail "backup creation failed; uninstall aborted"
  VERIFY_DIR="$(mktemp -d /tmp/vast-revenue-verify.XXXXXX)"
  (cd "${SOURCE_DIR}" && python3.12 -m src.backup "${BACKUP_FILE}" "${VERIFY_DIR}")
  rm -rf "${VERIFY_DIR}"
  log "Backup created: ${BACKUP_FILE}"
fi

log "Stopping and disabling ${SERVICE_FILE}..."
systemctl stop "${SERVICE_FILE}" 2>/dev/null || true
systemctl disable "${SERVICE_FILE}" 2>/dev/null || true
rm -f -- "${UNIT_PATH}"
rm -f -- /etc/cron.d/vast-revenue-monitor
systemctl daemon-reload
systemctl reset-failed "${SERVICE_FILE}" 2>/dev/null || true

if [[ "${PURGE}" == true || "${PURGE}" == backup ]]; then
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
fi
