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

## Installation on Ubuntu 24.04 LTS

### Shortest interactive installation

On a clean Ubuntu 24.04 server, install Git, clone the repository, and run the
installer once. Replace `<repository-url>` with this GitHub repository's clone URL.

```bash
sudo apt-get update && sudo apt-get install -y git
git clone <repository-url> vast-revenue-monitor
cd vast-revenue-monitor
sudo bash install.sh
```

The installer securely prompts for the Discord webhook URL and Vast.ai API key.
It then installs Ubuntu and Python dependencies, generates `config.json`, creates
all directories, installs the systemd unit, enables and starts the service, and
prints its final status. No manual virtual-environment or file-copy step is needed.

For unattended installation, pass credentials through `sudo --preserve-env`:

```bash
export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/.../...'
export VAST_API_KEY='your-vast-api-key'
sudo --preserve-env=DISCORD_WEBHOOK_URL,VAST_API_KEY bash install.sh
unset DISCORD_WEBHOOK_URL VAST_API_KEY
```

Validate the host and repository without changing the system:

```bash
sudo bash install.sh --check
```

Re-running `sudo bash install.sh` performs an upgrade. An existing
`/opt/vast-revenue-monitor/config.json`, `state/`, and `logs/` are preserved.
The new release is prepared and validated before activation; if activation fails,
the installer restores the previous release and restarts the previous service.

## Configuration

Copy `config.example.json` to `config.json` for local development. Configure:

- `discord_webhook_url`: Discord webhook endpoint.
- `vast_api_key`: Vast.ai API key.
- `daily_goal_usd`: Daily revenue target, default `120`.
- `timezone`: IANA timezone, default `Asia/Tokyo`.
- `exchange_api_urls`: ordered USDJPY provider URLs; each must return `rates.JPY` or `conversion_rates.JPY`.
- `log_level`: `DEBUG`, `INFO`, `WARNING`, or `ERROR`.

## Usage

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
sudo ./install.sh
sudo systemctl restart vast-balance.service
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
