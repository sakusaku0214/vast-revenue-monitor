#!/usr/bin/env bash
set -euo pipefail
APP_DIR="/opt/vast-revenue-monitor"
SERVICE_USER="vast-revenue-monitor"
SERVICE_FILE="vast-balance.service"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo ./install.sh" >&2
  exit 1
fi

for command in python3.12 rsync systemctl; do
  if ! command -v "${command}" >/dev/null 2>&1; then
    echo "Required command not found: ${command}" >&2
    exit 1
  fi
done

id -u "${SERVICE_USER}" >/dev/null 2>&1 || useradd --system --home "${APP_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
if systemctl cat "${SERVICE_FILE}" >/dev/null 2>&1; then
  systemctl stop "${SERVICE_FILE}"
fi
mkdir -p "${APP_DIR}" "${APP_DIR}/state" "${APP_DIR}/logs"
rsync -a \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'config.json' \
  --exclude 'state/' \
  --exclude 'logs/' \
  ./ "${APP_DIR}/"
python3.12 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
if [[ ! -f "${APP_DIR}/config.json" ]]; then
  cp "${APP_DIR}/config.example.json" "${APP_DIR}/config.json"
  echo "Created ${APP_DIR}/config.json; edit it with your credentials."
fi
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${APP_DIR}"
chmod 600 "${APP_DIR}/config.json"
chmod 700 "${APP_DIR}/state" "${APP_DIR}/logs"
cp "${APP_DIR}/systemd/${SERVICE_FILE}" "/etc/systemd/system/${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable "${SERVICE_FILE}"
systemctl restart "${SERVICE_FILE}"
systemctl status "${SERVICE_FILE}" --no-pager
