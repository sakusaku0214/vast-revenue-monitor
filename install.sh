#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/opt/vast-revenue-monitor"
SERVICE_USER="vast-revenue-monitor"
SERVICE_FILE="vast-balance.service"
UNIT_PATH="/etc/systemd/system/${SERVICE_FILE}"
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=false
MODE="install"
RESTORE_FILE=""
STAGING_DIR=""
BACKUP_DIR=""
UNIT_BACKUP=""
SERVICE_WAS_ACTIVE=false
INSTALL_COMMITTED=false
INSTALL_STARTED=false
APP_ACTIVATED=false
HAD_UNIT=false
USER_CREATED=false
GROUP_CREATED=false
CONFIG_BACKUP=""
RESTORE_ROLLBACK=""

log() {
  printf '[vast-revenue-monitor] %s\n' "$*"
}

fail() {
  printf '[vast-revenue-monitor] ERROR: %s\n' "$*" >&2
  exit 1
}

read_secret_twice() {
  local label=$1
  local output_name=$2
  local first=""
  local second=""
  read -r -s -p "${label}: " first
  printf '\n'
  read -r -s -p "${label} (confirm): " second
  printf '\n'
  [[ -n "${first}" ]] || fail "${label} must not be empty"
  [[ "${first}" == "${second}" ]] || fail "${label} entries did not match"
  printf -v "${output_name}" '%s' "${first}"
}

usage() {
  cat <<'EOF'
Usage: sudo bash install.sh [--check]

  --check   Validate the host and source tree without changing the system.
  --reconfigure  Update credentials, weekly goal, exchange APIs, and report detail.
  --backup       Back up config and state to a timestamped tar.gz.
  --restore FILE Restore config and state from a backup archive.

For unattended installation, set DISCORD_WEBHOOK_URL and VAST_API_KEY.
Without them, a new installation prompts securely for both values.
EOF
}

cleanup() {
  local exit_code=$?
  trap - ERR EXIT
  if [[ "${INSTALL_COMMITTED}" != true \
    && "${MODE}" == "install" \
    && "${INSTALL_STARTED}" == true ]]; then
    printf '[vast-revenue-monitor] ERROR: installation failed; rolling back.\n' >&2
    if [[ -n "${BACKUP_DIR}" && -d "${BACKUP_DIR}" ]]; then
      rm -rf -- "${APP_DIR}"
      mv -- "${BACKUP_DIR}" "${APP_DIR}"
    elif [[ "${APP_ACTIVATED}" == true ]]; then
      rm -rf -- "${APP_DIR}"
    fi
    if [[ -n "${UNIT_BACKUP}" && -f "${UNIT_BACKUP}" ]]; then
      cp -- "${UNIT_BACKUP}" "${UNIT_PATH}"
    elif [[ "${HAD_UNIT}" != true ]]; then
      systemctl disable "${SERVICE_FILE}" >/dev/null 2>&1 || true
      rm -f -- "${UNIT_PATH}"
    fi
    systemctl daemon-reload || true
    if [[ "${SERVICE_WAS_ACTIVE}" == true ]]; then
      systemctl start "${SERVICE_FILE}" || true
    fi
    if [[ "${USER_CREATED}" == true ]]; then
      userdel "${SERVICE_USER}" 2>/dev/null || true
    fi
    if [[ "${GROUP_CREATED}" == true ]]; then
      groupdel "${SERVICE_USER}" 2>/dev/null || true
    fi
  elif [[ "${INSTALL_COMMITTED}" != true && "${MODE}" != "install" ]]; then
    printf '[vast-revenue-monitor] ERROR: %s operation failed.\n' "${MODE}" >&2
    if [[ -n "${CONFIG_BACKUP}" && -f "${CONFIG_BACKUP}" ]]; then
      cp -a "${CONFIG_BACKUP}" "${APP_DIR}/config.json"
    fi
    if [[ -n "${RESTORE_ROLLBACK}" && -f "${RESTORE_ROLLBACK}" ]]; then
      rm -rf "${APP_DIR}/state"
      tar -xzf "${RESTORE_ROLLBACK}" -C "${APP_DIR}"
    fi
    systemctl start "${SERVICE_FILE}" 2>/dev/null || true
  fi
  [[ -z "${STAGING_DIR}" ]] || rm -rf -- "${STAGING_DIR}"
  [[ -z "${CONFIG_BACKUP}" ]] || rm -f -- "${CONFIG_BACKUP}"
  [[ -z "${RESTORE_ROLLBACK}" ]] || rm -f -- "${RESTORE_ROLLBACK}"
  exit "${exit_code}"
}

on_error() {
  local exit_code=$1
  local line=$2
  local command=$3
  printf '[vast-revenue-monitor] ERROR: command failed at line %s: %s\n' \
    "${line}" "${command}" >&2
  return "${exit_code}"
}

trap 'on_error "$?" "$LINENO" "$BASH_COMMAND"' ERR
trap cleanup EXIT

case "${1:-}" in
  --check) DRY_RUN=true; MODE="check" ;;
  --reconfigure) MODE="reconfigure" ;;
  --backup) MODE="backup" ;;
  --restore)
    MODE="restore"
    RESTORE_FILE="${2:-}"
    [[ -n "${RESTORE_FILE}" ]] || fail "--restore requires a tar.gz path"
    ;;
  --help|-h) usage; INSTALL_COMMITTED=true; exit 0 ;;
  "") ;;
  *) usage; exit 2 ;;
esac

[[ "${EUID}" -eq 0 ]] || fail "Run as root: sudo bash install.sh"
[[ -f "${SOURCE_DIR}/requirements.txt" ]] || fail "requirements.txt is missing"
[[ -f "${SOURCE_DIR}/config.example.json" ]] || fail "config.example.json is missing"
[[ -f "${SOURCE_DIR}/systemd/${SERVICE_FILE}" ]] || fail "systemd service is missing"
[[ -f "${SOURCE_DIR}/balance.py" ]] || fail "balance.py is missing"

if [[ "${MODE}" == "backup" ]]; then
  [[ -d "${APP_DIR}" ]] || fail "application is not installed"
  BACKUP_FILE="${PWD}/vast-revenue-monitor-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
  tar -czf "${BACKUP_FILE}" -C "${APP_DIR}" config.json state
  chmod 600 "${BACKUP_FILE}"
  if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != root ]]; then
    chown "${SUDO_USER}" "${BACKUP_FILE}"
  fi
  log "Backup created: ${BACKUP_FILE}"
  INSTALL_COMMITTED=true
  exit 0
fi

if [[ "${MODE}" == "restore" ]]; then
  [[ -d "${APP_DIR}" ]] || fail "install the application before restoring"
  [[ -f "${RESTORE_FILE}" ]] || fail "backup not found: ${RESTORE_FILE}"
  RESTORE_DIR="$(mktemp -d /tmp/vast-revenue-restore.XXXXXX)"
  (cd "${SOURCE_DIR}" && python3.12 -m src.backup \
    "${RESTORE_FILE}" "${RESTORE_DIR}")
  [[ -f "${RESTORE_DIR}/config.json" ]] || fail "backup has no config.json"
  CONFIG_BACKUP="$(mktemp /tmp/vast-config.XXXXXX.json)"
  cp -a "${APP_DIR}/config.json" "${CONFIG_BACKUP}"
  RESTORE_ROLLBACK="$(mktemp /tmp/vast-revenue-rollback.XXXXXX.tar.gz)"
  tar -czf "${RESTORE_ROLLBACK}" -C "${APP_DIR}" state
  systemctl stop "${SERVICE_FILE}" 2>/dev/null || true
  install -o root -g "${SERVICE_USER}" -m 0640 \
    "${RESTORE_DIR}/config.json" "${APP_DIR}/config.json"
  (cd "${APP_DIR}" && .venv/bin/python -c \
    'from pathlib import Path; from src.config import AppConfig; AppConfig.load(Path("config.json"))')
  rm -rf "${APP_DIR}/state"
  install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0700 "${APP_DIR}/state"
  [[ ! -d "${RESTORE_DIR}/state" ]] || rsync -a "${RESTORE_DIR}/state/" "${APP_DIR}/state/"
  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${APP_DIR}/state"
  rm -rf "${RESTORE_DIR}"
  systemctl restart "${SERVICE_FILE}"
  rm -f "${RESTORE_ROLLBACK}"; RESTORE_ROLLBACK=""
  rm -f "${CONFIG_BACKUP}"; CONFIG_BACKUP=""
  log "Restore completed from ${RESTORE_FILE}"
  INSTALL_COMMITTED=true
  exit 0
fi

if [[ "${MODE}" == "reconfigure" ]]; then
  [[ -f "${APP_DIR}/config.json" ]] || fail "application is not installed"
  CONFIG_BACKUP="$(mktemp /tmp/vast-config.XXXXXX.json)"
  cp -a "${APP_DIR}/config.json" "${CONFIG_BACKUP}"
  read_secret_twice "Discord webhook URL" DISCORD_WEBHOOK_URL
  read_secret_twice "Vast.ai API key" VAST_API_KEY
  read -r -p 'Weekly revenue goal (USD) [1000]: ' WEEKLY_GOAL_USD
  WEEKLY_GOAL_USD="${WEEKLY_GOAL_USD:-1000}"
  read -r -p 'Exchange API URLs, comma-separated [keep current]: ' EXCHANGE_API_URLS
  read -r -p 'Detailed report? [y/N]: ' detailed_answer
  DETAILED_REPORT=false
  [[ "${detailed_answer:-}" =~ ^[Yy]$ ]] && DETAILED_REPORT=true
  export DISCORD_WEBHOOK_URL VAST_API_KEY WEEKLY_GOAL_USD EXCHANGE_API_URLS DETAILED_REPORT
  python3.12 - "${APP_DIR}/config.json" <<'PY'
import json, os, sys, tempfile
from pathlib import Path
path = Path(sys.argv[1]); data = json.loads(path.read_text(encoding="utf-8"))
data.update(discord_webhook_url=os.environ["DISCORD_WEBHOOK_URL"],
            vast_api_key=os.environ["VAST_API_KEY"],
            weekly_goal_usd=float(os.environ["WEEKLY_GOAL_USD"]),
            detailed_report=os.environ["DETAILED_REPORT"] == "true")
if os.environ["EXCHANGE_API_URLS"].strip():
    data["exchange_api_urls"] = [u.strip() for u in os.environ["EXCHANGE_API_URLS"].split(",") if u.strip()]
fd, name = tempfile.mkstemp(dir=path.parent); os.close(fd)
Path(name).write_text(json.dumps(data, indent=2) + "\n")
Path(name).chmod(0o640); Path(name).replace(path)
PY
  chown "root:${SERVICE_USER}" "${APP_DIR}/config.json"
  (cd "${APP_DIR}" && .venv/bin/python -c \
    'from pathlib import Path; from src.config import AppConfig; AppConfig.load(Path("config.json"))')
  systemctl stop "${SERVICE_FILE}" 2>/dev/null || true
  (cd "${APP_DIR}" && runuser --user "${SERVICE_USER}" -- \
    .venv/bin/python balance.py --config config.json --validate)
  systemctl restart "${SERVICE_FILE}"
  rm -f "${CONFIG_BACKUP}"; CONFIG_BACKUP=""
  log "Configuration updated and service restarted."
  INSTALL_COMMITTED=true
  exit 0
fi

if [[ "${DRY_RUN}" == true ]]; then
  command -v systemctl >/dev/null || fail "systemctl is not installed"
  command -v apt-get >/dev/null || fail "apt-get is not installed"
  log "Source files and required host tools are present."
  if [[ -f "${APP_DIR}/config.json" ]]; then
    log "Existing config.json will be preserved."
  else
    log "A new config.json will be generated and credentials will be requested."
  fi
  log "Validation completed; no changes were made."
  INSTALL_COMMITTED=true
  exit 0
fi

export DEBIAN_FRONTEND=noninteractive
INSTALL_STARTED=true
log "Installing Ubuntu packages required by the service..."
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates python3.12 python3.12-venv rsync

if systemctl is-active --quiet "${SERVICE_FILE}"; then
  SERVICE_WAS_ACTIVE=true
fi
if [[ -f "${UNIT_PATH}" ]]; then
  HAD_UNIT=true
fi

STAGING_DIR="$(mktemp -d /opt/.vast-revenue-monitor.new.XXXXXX)"
log "Preparing a complete release in ${STAGING_DIR}..."
rsync -a \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'config.json' \
  --exclude 'state/' \
  --exclude 'logs/' \
  "${SOURCE_DIR}/" "${STAGING_DIR}/"

python3.12 -m venv "${STAGING_DIR}/.venv"
"${STAGING_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${STAGING_DIR}/.venv/bin/python" -m pip install \
  -r "${STAGING_DIR}/requirements.txt"

if [[ -f "${APP_DIR}/config.json" ]]; then
  log "Preserving existing config.json exactly as-is."
  cp -a -- "${APP_DIR}/config.json" "${STAGING_DIR}/config.json"
else
  if [[ -z "${DISCORD_WEBHOOK_URL:-}" ]]; then
    [[ -t 0 ]] || fail "Set DISCORD_WEBHOOK_URL for non-interactive installation"
    read_secret_twice "Discord webhook URL" DISCORD_WEBHOOK_URL
  fi
  if [[ -z "${VAST_API_KEY:-}" ]]; then
    [[ -t 0 ]] || fail "Set VAST_API_KEY for non-interactive installation"
    read_secret_twice "Vast.ai API key" VAST_API_KEY
  fi
  read -r -p 'Weekly revenue goal (USD) [1000]: ' WEEKLY_GOAL_USD
  WEEKLY_GOAL_USD="${WEEKLY_GOAL_USD:-1000}"
  read -r -p 'Detailed report? [y/N]: ' detailed_answer
  DETAILED_REPORT=false
  [[ "${detailed_answer:-}" =~ ^[Yy]$ ]] && DETAILED_REPORT=true
  export DISCORD_WEBHOOK_URL VAST_API_KEY WEEKLY_GOAL_USD DETAILED_REPORT
  cp -- "${STAGING_DIR}/config.example.json" "${STAGING_DIR}/config.json"
  "${STAGING_DIR}/.venv/bin/python" - "${STAGING_DIR}/config.json" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
config = json.loads(path.read_text(encoding="utf-8"))
config["discord_webhook_url"] = os.environ["DISCORD_WEBHOOK_URL"]
config["vast_api_key"] = os.environ["VAST_API_KEY"]
config["weekly_goal_usd"] = float(os.environ["WEEKLY_GOAL_USD"])
config["detailed_report"] = os.environ["DETAILED_REPORT"] == "true"
path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
PY
  unset DISCORD_WEBHOOK_URL VAST_API_KEY
  log "Generated config.json from config.example.json."
fi

mkdir -p "${STAGING_DIR}/state" "${STAGING_DIR}/logs"
systemctl stop "${SERVICE_FILE}" 2>/dev/null || true
if [[ -d "${APP_DIR}/state" ]]; then
  rsync -a "${APP_DIR}/state/" "${STAGING_DIR}/state/"
fi
if [[ -d "${APP_DIR}/logs" ]]; then
  rsync -a "${APP_DIR}/logs/" "${STAGING_DIR}/logs/"
fi

(
  cd "${STAGING_DIR}"
  .venv/bin/python -c \
    'from pathlib import Path; from src.config import AppConfig; AppConfig.load(Path("config.json"))'
) || fail "config.json validation failed; existing installation was not changed"

if ! getent group "${SERVICE_USER}" >/dev/null 2>&1; then
  groupadd --system "${SERVICE_USER}"
  GROUP_CREATED=true
fi
if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --gid "${SERVICE_USER}" --home-dir "${APP_DIR}" \
    --shell /usr/sbin/nologin "${SERVICE_USER}"
  USER_CREATED=true
fi
chown -R root:root "${STAGING_DIR}"
chown "root:${SERVICE_USER}" "${STAGING_DIR}/config.json"
chown -R "${SERVICE_USER}:${SERVICE_USER}" \
  "${STAGING_DIR}/state" "${STAGING_DIR}/logs"
chmod 755 "${STAGING_DIR}"
chmod 640 "${STAGING_DIR}/config.json"
chmod 700 "${STAGING_DIR}/state" "${STAGING_DIR}/logs"

log "Validating Vast.ai and exchange-rate API connectivity..."
if ! (
  cd "${STAGING_DIR}"
  runuser --user "${SERVICE_USER}" -- \
    .venv/bin/python balance.py --config config.json --validate
); then
  if [[ -f "${STAGING_DIR}/logs/api_response.json" ]]; then
    install -o root -g root -m 0600 \
      "${STAGING_DIR}/logs/api_response.json" \
      /tmp/vast-revenue-monitor-api_response.json
    log "Saved the failed Vast.ai response to /tmp/vast-revenue-monitor-api_response.json"
  fi
  fail "upstream API validation failed; the service was not activated"
fi

log "Activating the prepared release..."
if [[ -d "${APP_DIR}" ]]; then
  BACKUP_DIR="$(mktemp -d /opt/.vast-revenue-monitor.old.XXXXXX)"
  rmdir "${BACKUP_DIR}"
  mv -- "${APP_DIR}" "${BACKUP_DIR}"
fi
mv -- "${STAGING_DIR}" "${APP_DIR}"
APP_ACTIVATED=true
STAGING_DIR=""
if [[ -f "${UNIT_PATH}" ]]; then
  UNIT_BACKUP="$(mktemp /tmp/vast-balance.service.XXXXXX)"
  cp -- "${UNIT_PATH}" "${UNIT_BACKUP}"
fi
install -o root -g root -m 0644 \
  "${APP_DIR}/systemd/${SERVICE_FILE}" "${UNIT_PATH}"

systemctl daemon-reload
systemctl enable "${SERVICE_FILE}"
systemctl restart "${SERVICE_FILE}"
sleep 2
systemctl is-active --quiet "${SERVICE_FILE}" || \
  fail "service did not become active; inspect: journalctl -u ${SERVICE_FILE}"
systemctl status "${SERVICE_FILE}" --no-pager

INSTALL_COMMITTED=true
[[ -z "${BACKUP_DIR}" ]] || rm -rf -- "${BACKUP_DIR}"
[[ -z "${UNIT_BACKUP}" ]] || rm -f -- "${UNIT_BACKUP}"
log "Installation completed successfully."
