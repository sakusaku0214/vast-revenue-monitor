# Vast Revenue Monitor v1.0.0

Vast Revenue Monitor v1.0.0 is the first stable release of the production-oriented
Ubuntu service for monitoring Vast.ai balance-based revenue and delivering hourly
Discord reports in USD and JPY.

## Highlights

- Compact hourly Discord reports with Hourly, Daily, current Weekly balance,
  independent Weekly Goal progress, all-time highs, USDJPY, and JST time.
- Optional detailed reports with revenue changes and daily-goal pace information.
- Separate gold Discord embeds for new Hourly, Daily, Weekly, and Monthly records.
- Balance-based latest-interval and 09:00 JST business-day revenue estimation.
- Correct latest-interval Hourly calculation with no rolling-window double count,
  normalization, or extrapolation.
- English and Japanese notification languages with install-time selection and
  post-install language switching.
- Saturday 09:00 JST weekly reset handling that preserves the pre-reset weekly high
  and correctly starts the new week from the first post-reset balance.
- Three-provider USDJPY failover with a persistent last-known-good cache.
- Atomic JSON state, yearly CSV history, persistent records, and compressed rotating
  logs with 30-day retention.

## Installation and Operations

- Transactional Ubuntu 24.04 installer with dependency installation, secure
  credential prompts, API validation, rollback, systemd enablement, and hardening.
- `install.sh --reconfigure` and the supported
  `/opt/vast-revenue-monitor/reconfigure.sh` command for safe language and Weekly
  Goal changes without reinstalling or exposing credentials.
- `install.sh --backup` and `install.sh --restore` for migration and disaster
  recovery.
- Complete uninstall with optional validated backup before all generated files and
  the dedicated service account are removed.
- Safe restore validation against path traversal, unsafe archive entries, excessive
  file counts, and oversized expanded archives.

## Security

- Dedicated non-login service account and hardened systemd sandbox.
- Root-owned application code with narrowly scoped state/log write access.
- Restricted permissions for configuration, state, diagnostics, and backups.
- Redaction of credentials and personal fields in persisted Vast.ai diagnostics.
- HTTPS-only endpoint validation and retry/time-out policies for network clients.

## Quality

- Python 3.12+ with type hints and modular business/I/O boundaries.
- Comprehensive pytest coverage for configuration, APIs, revenue boundaries,
  persistence, records, backup safety, Discord rendering, and scheduler failures.
- GitHub Actions runs pytest and ShellCheck on pushes and pull requests.
- Complete English (`README.md`) and Japanese (`README.ja.md`) documentation.

## Upgrade to v1.0.0

```bash
cd ~/vast-revenue-monitor
git pull
git log -1 --oneline
sudo bash install.sh --check
sudo bash install.sh
sudo systemctl status vast-balance.service --no-pager -l
```

The installer preserves an existing `config.json`, `state/`, and `logs/`. Create a
backup before upgrading when migrating an important installation:

```bash
sudo bash install.sh --backup
```

## Important Notes

- Backup archives contain the Vast.ai API key and Discord webhook. Store them
  securely and never commit or publish them.
- Revenue is estimated from observed positive changes in the Vast.ai account
  balance. Changes occurring between samples or across the 09:00 JST boundary
  cannot be attributed more precisely than the observation data allows.
- This is an unofficial tool and is not affiliated with or endorsed by Vast.ai.

For complete installation, configuration, backup, restore, troubleshooting, and
uninstall instructions, see `README.md`.
