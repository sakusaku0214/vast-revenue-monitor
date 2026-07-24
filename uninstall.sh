#!/usr/bin/env bash
set -euo pipefail
SERVICE_FILE="vast-balance.service"
APP_DIR="/opt/vast-revenue-monitor"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo ./uninstall.sh" >&2
  exit 1
fi

systemctl stop "${SERVICE_FILE}" 2>/dev/null || true
systemctl disable "${SERVICE_FILE}" 2>/dev/null || true
rm -f "/etc/systemd/system/${SERVICE_FILE}"
systemctl daemon-reload
read -r -p "Remove ${APP_DIR} including state and logs? [y/N] " answer
if [[ "${answer}" =~ ^[Yy]$ ]]; then
  rm -rf "${APP_DIR}"
fi
