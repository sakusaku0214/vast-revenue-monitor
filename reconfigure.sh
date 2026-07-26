#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/vast-revenue-monitor}"
SERVICE_FILE="vast-balance.service"
SERVICE_USER="vast-revenue-monitor"
CONFIG="${CONFIG_PATH:-${APP_DIR}/config.json}"
PYTHON="${PYTHON:-${APP_DIR}/.venv/bin/python}"

[[ ${EUID} -eq 0 || ${ALLOW_NON_ROOT:-} == 1 ]] || { echo "Run as root: sudo ${APP_DIR}/reconfigure.sh" >&2; exit 1; }
[[ -f ${CONFIG} ]] || { echo "Configuration not found: ${CONFIG}" >&2; exit 1; }
[[ -x ${PYTHON} ]] || { echo "Installed Python is missing: ${PYTHON}" >&2; exit 1; }

set +e
"${PYTHON}" "${APP_DIR}/src/reconfigure_config.py" "${CONFIG}"
result=$?
set -e
[[ ${result} -ne 3 ]] || exit 0
[[ ${result} -eq 0 ]] || exit "${result}"
chown "root:${SERVICE_USER}" "${CONFIG}" 2>/dev/null || [[ ${ALLOW_NON_ROOT:-} == 1 ]]
chmod 0640 "${CONFIG}"
if [[ ${SKIP_SERVICE_RESTART:-} == 1 ]]; then
  echo "Configuration updated (service restart skipped)."
elif ! systemctl restart "${SERVICE_FILE}"; then
  echo "Configuration saved, but service restart failed." >&2
  echo "Recover with: sudo systemctl restart ${SERVICE_FILE}" >&2
  exit 1
else
  echo "Configuration updated and ${SERVICE_FILE} restarted."
fi
