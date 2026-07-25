# vast-revenue-monitor

Production-ready Python 3.12+ service for monitoring Vast.ai revenue and posting hourly Discord webhook embed reports in USD and JPY.

## Features

- Hourly, daily, weekly, and monthly revenue reporting.
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
git clone <repository-url> vast-revenue-monitor
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
sudo --preserve-env=DISCORD_WEBHOOK_URL,VAST_API_KEY bash install.sh
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
- `timezone`: IANA timezone, default `Asia/Tokyo`.
- `exchange_api_urls`: ordered USDJPY provider URLs; each must return `rates.JPY` or `conversion_rates.JPY`.
- `log_level`: `DEBUG`, `INFO`, `WARNING`, or `ERROR`.

## Usage

### How revenue is calculated

The current-user endpoint exposes account values such as `balance`; it does not
provide hourly, daily, weekly, and monthly revenue totals. The monitor therefore
stores successive balance samples in `state/revenue_events.json` and counts only
positive changes as observed revenue. Hourly, 09:00 business-day, Saturday 09:00
weekly, and first-day 09:00 monthly totals are aggregated from those events.

The first successful sample establishes a baseline and reports zero revenue. Totals
become accurate as the service observes subsequent changes. A payout lowers the
balance and is treated as zero revenue, but earnings and a payout occurring between
two samples cannot be separated using this endpoint alone. Set
`vast_balance_field` to `paid_expected` only after confirming that value increases
monotonically for the account.

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
