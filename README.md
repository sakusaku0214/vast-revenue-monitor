# vast-revenue-monitor

Production-ready Python 3.12+ service for monitoring Vast.ai revenue and posting hourly Discord webhook embed reports in USD and JPY.

## Features

- Hourly, daily, weekly, and monthly revenue reporting.
- Live USDJPY conversion with persistent fallback cache.
- Professional Discord embeds with amount and percentage changes.
- Persistent records for highest hourly, daily, weekly, and monthly revenue.
- Gold Discord embed and `🎉 NEW RECORD` when a record is broken.
- Daily business goal tracking for a 09:00 JST to 09:00 JST business day.
- Adaptive weekly reset learner for the Saturday around 09:00 JST reset window.
- Rotating logs, JSON state files, and CSV history export for forecasting.
- Modular architecture prepared for Prometheus, Grafana, Slack, LINE, web UI, SQLite, and PostgreSQL extensions.

## Installation on Ubuntu 24.04 LTS

```bash
git clone <repo-url> vast-revenue-monitor
cd vast-revenue-monitor
sudo ./install.sh
```

Edit `/opt/vast-revenue-monitor/config.json` and restart:

```bash
sudo systemctl restart vast-balance.service
```

## Configuration

Copy `config.example.json` to `config.json` for local development. Configure:

- `discord_webhook_url`: Discord webhook endpoint.
- `vast_api_key`: Vast.ai API key.
- `daily_goal_usd`: Daily revenue target, default `120`.
- `timezone`: IANA timezone, default `Asia/Tokyo`.
- `exchange_api_url`: USD exchange-rate endpoint returning `rates.JPY`.
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

The service automatically creates JSON files under `state/`:

- `history.json`
- `history.csv`
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
pytest
```
