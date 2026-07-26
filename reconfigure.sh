#!/usr/bin/env bash
set -Eeuo pipefail
APP_DIR="/opt/vast-revenue-monitor"
SERVICE="vast-balance.service"
[[ "${EUID}" -eq 0 ]] || { echo "Run as root: sudo ${APP_DIR}/reconfigure.sh" >&2; exit 1; }
if (cd "${APP_DIR}" && .venv/bin/python -m src.reconfigure); then
  chown root:vast-revenue-monitor "${APP_DIR}/config.json"
  chmod 640 "${APP_DIR}/config.json"
  echo "Restarting ${SERVICE}..."
  if ! systemctl restart "${SERVICE}"; then
    echo "Restart failed. Recover with: sudo systemctl restart ${SERVICE}" >&2
    exit 1
  fi
  echo "Service restarted successfully."
fi
