# vast-revenue-monitor

<p align="center">
  <img src="https://github.com/user-attachments/assets/4698af2b-3d8e-4d86-b5d8-8344717fcea3"
       alt="Vast Revenue Monitor Discord notification"
       width="465">
</p>


English | [日本語](README.ja.md)

**Current Stable Release: v1.0.0**

Production-ready Python 3.12+ service for monitoring Vast.ai revenue and posting hourly Discord webhook embed reports in USD and JPY.

## Features

- Latest-interval (“Hourly”), daily, weekly, and monthly revenue reporting in English or Japanese. Hourly is the actual positive increment in the newest successful monitoring interval; it is not a normalized hourly rate.
- Live USDJPY conversion using three providers with persistent fallback cache.
- Professional Discord embeds with amount and percentage changes.
- Persistent records for highest hourly, daily, weekly, and monthly revenue.
- Gold Discord embed and `🎉 NEW RECORD` when a record is broken.
- Daily business goal tracking for a 09:00 JST to 09:00 JST business day.
- Adaptive weekly reset learner for the Saturday around 09:00 JST reset window.
- 30-day compressed log rotation, JSON state files, and yearly CSV history export.
- Modular architecture prepared for Prometheus, Grafana, Slack, LINE, web UI, SQLite, and PostgreSQL extensions.

## Complete installation on a clean Ubuntu 24.04 LTS server

### Prerequisites

The server needs working DNS, HTTPS internet access, and a user with `sudo` access.
Have the following credentials ready:

1. A Discord webhook URL created for the destination channel.
2. A Vast.ai API key.

No Python, virtual environment, `rsync`, system user, or systemd service needs to
be configured manually.

### Step 1: install Git and clone the project

Git is required only to clone the repository. Replace `<repository-url>` with the
HTTPS clone URL shown by GitHub's **Code** button.

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/sakusaku0214/vast-revenue-monitor.git
cd vast-revenue-monitor
```

### Step 2: optional non-destructive validation

This checks the repository and host tools without installing or changing files:

```bash
sudo bash install.sh --check
```

The final line should be:

```text
[vast-revenue-monitor] Validation completed; no changes were made.
```

### Step 3: run the installer once

```bash
sudo bash install.sh
```

Enter the Discord webhook URL and Vast.ai API key when prompted. Each secret must
be entered twice; a mismatch stops installation. Input is hidden, including the
webhook because its token grants permission to post to Discord. The installer then:

1. Installs `ca-certificates`, Python 3.12, `python3.12-venv`, and `rsync` with APT.
2. Builds and validates a complete release in a temporary directory.
3. Creates `config.json` from `config.example.json` on the first installation.
4. Creates the Python virtual environment and installs all Python dependencies.
5. Creates `state/` and `logs/`, the service user, ownership, and permissions.
6. Installs the systemd unit and runs `daemon-reload`, `enable`, and `restart`.
7. Confirms that the service is active and prints `systemctl status`.

Before activation, the installer calls Vast.ai, an exchange-rate provider, and
Discord's webhook information endpoint. It does not post a Discord message or
modify revenue history during this check. Invalid credentials, schema errors, or
connectivity failures stop installation instead of reporting success for a running
but non-functional service.

Success ends with:

```text
[vast-revenue-monitor] Installation completed successfully.
```

If any command fails, the message includes the command and line number. An upgrade
restores the prior application, unit, and running service. A failed first install
removes the incomplete application and unit.

### Step 4: verify operation

```bash
sudo systemctl is-enabled vast-balance.service
sudo systemctl is-active vast-balance.service
sudo systemctl status vast-balance.service --no-pager
sudo journalctl -u vast-balance.service -n 50 --no-pager
```

The first two commands must print `enabled` and `active`. API or webhook errors are
shown by the journal command and in
`/opt/vast-revenue-monitor/logs/vast-revenue-monitor.log`.

### Vast.ai schema validation errors

`VastApiSchemaError` means the process is running, but the received Vast.ai JSON
does not contain the revenue fields understood by this version. It is a real
application error; `active (running)` alone does not mean reports are working.

On every schema parsing failure, the complete response is saved with private file
permissions to:

```text
/opt/vast-revenue-monitor/logs/api_response.json
```

During a new installation or upgrade, API validation happens before activation.
If it fails, the staged installation is rolled back and the response is retained at:

```text
/tmp/vast-revenue-monitor-api_response.json
```

Inspect field names without posting secret values publicly:

```bash
sudo python3 -m json.tool /tmp/vast-revenue-monitor-api_response.json
sudo journalctl -u vast-balance.service -n 100 -l --no-pager
```

Installed files are located at:

```text
/opt/vast-revenue-monitor/
├── .venv/
├── config.json
├── logs/
├── state/
├── src/
├── systemd/
└── balance.py
```

`config.json` is readable only by root and the service group. Application code is
root-owned, while the service can write only its `state/` and `logs/` directories.

### Unattended installation

For unattended installation, pass credentials through `sudo --preserve-env`:

```bash
export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/.../...'
export VAST_API_KEY='your-vast-api-key'
export NOTIFICATION_LANGUAGE=ja # optional: en (default) or ja
sudo --preserve-env=DISCORD_WEBHOOK_URL,VAST_API_KEY,NOTIFICATION_LANGUAGE bash install.sh
unset DISCORD_WEBHOOK_URL VAST_API_KEY
```

### Re-running and upgrading

Re-running `sudo bash install.sh` performs an upgrade. An existing
`/opt/vast-revenue-monitor/config.json`, `state/`, and `logs/` are preserved.
The new release is prepared and validated before activation; if activation fails,
the installer restores the previous release and restarts the previous service.

## Configuration

Copy `config.example.json` to `config.json` for local development. Configure:

- `discord_webhook_url`: Discord webhook endpoint.
- `vast_api_key`: Vast.ai API key.
- `vast_revenue_endpoint`: Vast.ai endpoint path, default `/users/current/`.
- `vast_auth_mode`: `query` sends the key as `?api_key=...`; `bearer` uses the
  Authorization header. The current-user endpoint defaults to `query`.
- `vast_balance_field`: account counter used for local revenue deltas, default
  `balance`; advanced users may select `paid_expected` if it is monotonic for their
  Vast.ai account.
- `daily_goal_usd`: Daily revenue target, default `120`.
- `weekly_goal_usd`: independent weekly target, prompted during installation and
  defaulting to `1000` USD.
- `language`: Discord notification language, `en` (default) or `ja`.
- `detailed_report`: `false` sends the compact hourly report; `true` adds changes
  and daily-goal pace details.
- `timezone`: IANA timezone, default `Asia/Tokyo`.
- `exchange_api_urls`: ordered USDJPY provider URLs; each must return `rates.JPY` or `conversion_rates.JPY`.
- `log_level`: `DEBUG`, `INFO`, `WARNING`, or `ERROR`.

## Usage

### How revenue is calculated

The current-user endpoint exposes the weekly `balance`; it does not
provide hourly, daily, weekly, and monthly revenue totals. The monitor therefore
stores successive balance samples in `state/revenue_events.json` and counts only
positive changes as observed revenue. Hourly, 09:00 business-day, Saturday 09:00
weekly, and first-day 09:00 monthly totals are aggregated from those events.

The first successful sample establishes a baseline and reports zero revenue. A
balance decrease contributes no negative revenue but always becomes the next
baseline. When a sample crosses the Saturday 09:00 JST reset, the prior balance is
archived in the reset event and the new balance is counted from zero, so earnings
between 09:00 and the first post-reset sample are retained. Null, string, or boolean
balances are rejected before state is changed. `paid_expected` and `paid_verified`
are not used by default.

The default compact Discord report contains Hourly, Daily, and current Vast
`balance` as Weekly revenue; an independent Weekly Goal; all-time highs; USDJPY;
and local time. New records are sent as separate small gold embeds. Set
`detailed_report` to `true` to additionally show monthly/change and daily-goal pace
details.

Run once for validation:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
python balance.py --config config.json --once
```

Run continuously:

```bash
python balance.py --config config.json
```

## State files

The service automatically creates state files under `state/`:

- `history.json`
- `history-YYYY.csv`
- `revenue_events.json`
- `records.json`
- `weekly_reset.json`
- `exchange_rate.json`
- `goal.json`

## Systemd commands

```bash
sudo systemctl status vast-balance.service
sudo systemctl restart vast-balance.service
sudo journalctl -u vast-balance.service -f
```

## Clean removal and fresh reinstall

Back up anything needed first. A purge permanently removes `config.json`, all
revenue history and records, logs, the virtual environment, systemd unit, and the
service user/group. It does not uninstall shared Ubuntu packages.

Optional backup:

```bash
sudo systemctl stop vast-balance.service
sudo tar -czf "$HOME/vast-revenue-monitor-backup-$(date +%F).tar.gz" \
  -C /opt/vast-revenue-monitor config.json state logs
```

Completely remove the current installation. Answer `Y` (or press Enter) when asked
whether logs and history should be deleted:

```bash
cd ~/vast-revenue-monitor
sudo bash uninstall.sh --purge
```

Verify that no installed service or application directory remains:

```bash
test ! -e /opt/vast-revenue-monitor && echo "application removed"
test ! -e /etc/systemd/system/vast-balance.service && echo "unit removed"
systemctl status vast-balance.service --no-pager || true
```

Install from scratch and enter the Discord webhook and Vast.ai API key twice:

```bash
git pull
sudo bash install.sh
sudo systemctl status vast-balance.service --no-pager
sudo journalctl -u vast-balance.service -n 100 -l --no-pager
```

Running `sudo bash uninstall.sh` shows the same `Delete all logs and history?
[Y/n]` choice. `Y` completely removes all generated files, while `N` removes the
service/runtime but preserves only `config.json` and `state/` for a later install.
For automated environments only, `sudo bash uninstall.sh --purge --yes` skips the
confirmation.

## Reconfigure without reinstalling

```bash
sudo /opt/vast-revenue-monitor/reconfigure.sh
# Backward-compatible alias:
sudo /opt/vast-revenue-monitor/install.sh --reconfigure
```

This displays the current Weekly Goal and notification language, preserves either
value when Enter is pressed, and asks for confirmation. Only `weekly_goal_usd` and
`language` are atomically updated; credentials, unknown keys, state, and history
remain unchanged. The service is restarted only after a successful write.

## Backup and restore commands

Create a private timestamped archive containing `config.json` and the complete
`state/` tree (records, JSON/CSV history, reset learning, and revenue events):

```bash
cd ~/vast-revenue-monitor
sudo bash install.sh --backup
```

Restore after installing the application on the same or another machine:

```bash
sudo bash install.sh --restore /path/to/vast-revenue-monitor-backup-YYYYMMDD-HHMMSS.tar.gz
```

Restore validates archive paths, stops the service, restores private ownership and
permissions, and restarts the service. Keep archives private because they contain
the Discord webhook and Vast.ai API key.

## Upgrade procedure

```bash
cd /path/to/vast-revenue-monitor
git pull
sudo bash install.sh
```

Before upgrading, back up `/opt/vast-revenue-monitor/config.json` and the `state/`
directory. The installer stops the existing service before deployment, preserves
`config.json`, `state/`, and `logs/`, recreates the virtual environment, reinstalls
dependencies, reloads systemd, and restarts the service. Do not run two copies of
the monitor against the same state directory; a process lock rejects that setup.

## Backup and restore

Create a backup:

```bash
sudo systemctl stop vast-balance.service
sudo tar -czf vast-revenue-monitor-backup.tar.gz \
  -C /opt/vast-revenue-monitor config.json state logs
sudo systemctl start vast-balance.service
```

Restore a backup:

```bash
sudo systemctl stop vast-balance.service
sudo tar -xzf vast-revenue-monitor-backup.tar.gz -C /opt/vast-revenue-monitor
sudo chown -R vast-revenue-monitor:vast-revenue-monitor \
  /opt/vast-revenue-monitor/config.json \
  /opt/vast-revenue-monitor/state \
  /opt/vast-revenue-monitor/logs
sudo systemctl start vast-balance.service
```

## Troubleshooting

- Confirm `config.json` contains a valid Discord webhook and Vast.ai API key.
- Use `log_level: "DEBUG"` for more API and scheduler diagnostics.
- Check `logs/vast-revenue-monitor.log` and `journalctl -u vast-balance.service`.
- If exchange-rate API is down, ensure `state/exchange_rate.json` contains a previous successful rate.
- If Vast.ai parsing fails, set `log_level` to `DEBUG` and inspect `logs/api_response.json`.

## Screenshots

![Discord revenue embed placeholder](docs/images/discord-embed-placeholder.png)

## Development notes

The code separates configuration, API clients, notification rendering, state persistence, records, goals, and scheduling. New integrations should depend on domain models rather than concrete storage or notification implementations.

Run tests locally with:

```bash
pip install 'pytest>=8.3.2,<9'
pytest
```

## Post-install operation and reconfiguration

Run an immediate report with `sudo -u vast-revenue-monitor /opt/vast-revenue-monitor/.venv/bin/python /opt/vast-revenue-monitor/balance.py --config /opt/vast-revenue-monitor/config.json --once`. Check the installed CLI with `sudo /opt/vast-revenue-monitor/.venv/bin/python /opt/vast-revenue-monitor/balance.py --version`.

Change the Weekly Goal or notification language later with:

```bash
sudo /opt/vast-revenue-monitor/reconfigure.sh
```

The tool shows current values, accepts Enter to preserve either setting, reviews the proposal, and writes atomically only after confirmation. It preserves credentials, unknown settings, and every state/history file, then restarts `vast-balance.service`. Decimal positive goals are accepted; zero, negative, malformed, NaN, and infinite values are rejected. Choose `1`/`en` or `2`/`ja`.

### Supported backup, restore, and uninstall

```bash
sudo /opt/vast-revenue-monitor/install.sh --backup
sudo /opt/vast-revenue-monitor/install.sh --restore /path/to/vast-revenue-monitor-backup-YYYYMMDD-HHMMSS.tar.gz
sudo /opt/vast-revenue-monitor/uninstall.sh
```

Backups contain API credentials, the Discord webhook, and revenue history: keep them encrypted and mode `0600`, and never post them publicly. Restore accepts older compatible configurations without a `language` key (English is used). Ordinary upgrades use a fresh checkout of the desired release and `sudo bash install.sh`; existing configuration, state, history, records, logs, and exchange-rate cache are preserved.

### Troubleshooting, security, and disclaimer

Configuration is `/opt/vast-revenue-monitor/config.json`; runtime data is under `state/`, logs under `logs/`, and service logs are available with `sudo journalctl -u vast-balance.service`. If a restart fails, run `sudo systemctl restart vast-balance.service` and inspect the journal. Keep config and backups private, rotate credentials after suspected exposure, and do not run the service as root. Vast Revenue Monitor is provided without warranty; verify values against Vast.ai and do not treat reports as accounting, tax, or financial advice.

### English notification example

```text
💰 VAST.AI HOURLY REPORT
Revenue — Hourly $5.36 · Daily $20.00 · Weekly $95.00
Weekly Goal — Current $95.00 · Goal $100.00 · Remaining to Goal $5.00
Vast Revenue Monitor v1.0.0
```
