# vast.ai-revenue-monitor

![GitHub release](https://img.shields.io/github/v/release/sakusaku0214/vast-revenue-monitor)
![License](https://img.shields.io/github/license/sakusaku0214/vast-revenue-monitor)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
<br>
<img width="470" height="451" alt="image" src="https://github.com/user-attachments/assets/40390a29-eff8-4688-bdca-2a5dfefbce9e" />


<p>
  <strong>A production-ready revenue monitor for Vast.ai hosts with automatic Discord notifications.</strong>
</p>

<p>
  English | <a href="README.ja.md">日本語</a>
</p>

**Current stable release: v1.1.2**

---

# Overview

Vast Revenue Monitor is a monitoring service for Vast.ai hosts that periodically retrieves account revenue from the Vast.ai API and automatically posts rich Discord Embed reports.

The monitor tracks:

- Latest interval revenue
- Today's revenue
- Yesterday's revenue
- Current payout week
- Current payout month
- Weekly goal progress
- USD → JPY conversion
- All-Time High (ATH) statistics

Daily statistics reset at **09:00 JST**, while weekly statistics follow Vast.ai's payout cycle beginning every **Saturday at 09:00 JST**.

Delayed payout resets are detected automatically and confirmed only after an actual balance decrease, preventing false revenue spikes.

Designed for continuous production operation using **systemd**, with complete English and Japanese localization.

---

# Features

- 💰 Automatic Discord revenue reports
- 📈 Latest Interval / Today / Yesterday / This Week / This Month
- 🏆 Hourly / Daily / Weekly / Monthly ATH
- 🎯 Weekly revenue goal tracking
- 💴 Automatic USD → JPY conversion
- 🌏 English and Japanese notifications
- 📊 Compact and detailed report modes
- 🔒 Atomic state persistence
- 🔄 Safe one-command updates
- 🛠 Built-in state repair utility
- 🚀 Production-ready systemd service

---

# Revenue Periods

All period boundaries use the configured timezone (default: **Asia/Tokyo**).

| Period | Definition |
|---------|------------|
| Latest interval | Positive balance increase observed since the previous successful sample |
| Today | 09:00 JST until now |
| Yesterday | Previous completed 09:00 → 09:00 period |
| This week | Current payout week (Saturday 09:00 → now) |
| This month | Completed payout weeks belonging to the current payout month plus the running payout week |

Unlike calendar-based accounting, monthly revenue follows Vast.ai payout weeks.

Depending on the calendar, a payout month may contain **4 or 5 completed payout weeks**.

---

# All-Time High (ATH)

ATH values are calculated independently for completed periods.

| ATH | Updated when |
|------|--------------|
| Hourly | A completed revenue interval exceeds the previous record |
| Daily | A daily period (09:00 → 09:00) completes |
| Weekly | A payout week completes |
| Monthly | A payout month completes |

Hourly ATH is calculated only from valid positive revenue increments.

Daily, Weekly, and Monthly ATH are updated **only after the corresponding period has completed**, never from in-progress values.

---

# Discord Reports

### Compact report

Displays:

- Revenue
- Weekly goal progress
- ATH records
- Exchange rate

### Detailed report

Additionally includes:

- Revenue change since previous report
- Daily goal progress
- Current pace
- Expected pace
- Estimated end-of-day revenue
- Status summary

---

# Installation (Ubuntu 24.04 LTS)

Requirements:

- Ubuntu 24.04 LTS
- sudo privileges
- Discord Webhook URL
- Vast.ai API Key
- Working DNS and HTTPS connectivity

Clone the repository:

```bash
sudo apt-get update
sudo apt-get install -y git

git clone https://github.com/sakusaku0214/vast-revenue-monitor.git
cd vast-revenue-monitor
```

Optional validation:

```bash
sudo bash install.sh --check
```

Install:

```bash
sudo bash install.sh
```

The installer will prompt for:

- Discord Webhook URL
- Vast.ai API Key
- Weekly revenue goal
- Detailed report mode
- Notification language

Python, virtual environments, dependencies, and the systemd service are installed automatically.

---

# Updating

Recommended:

```bash
cd ~/vast-revenue-monitor
sudo ./update.sh
```

The updater safely:

- checks the repository state
- performs a fast-forward update
- preserves configuration and history
- reinstalls the application
- rolls back automatically if activation fails

Manual update:

```bash
git pull --ff-only origin main
sudo bash install.sh
```

---

# Configuration

Configuration file:

```text
/opt/vast-revenue-monitor/config.json
```

Important options:

| Setting | Description |
|---------|-------------|
| weekly_goal_usd | Weekly revenue goal |
| daily_goal_usd | Daily revenue goal |
| language | en / ja |
| detailed_report | Enable detailed reporting |
| timezone | Timezone used for revenue boundaries |
| state_dir | State storage directory |
| log_dir | Log directory |

Relative paths are resolved relative to the directory containing `config.json`, not the current working directory.

---

# Reconfiguration

After installation you can change:

- Weekly goal
- Notification language
- Detailed report mode

using:

```bash
sudo /opt/vast-revenue-monitor/reconfigure.sh
```

Configuration changes restart the service only if values actually changed.

A confirmation notification is sent immediately after successful reconfiguration.

---

# State Repair

Older releases may contain corrupted revenue history caused by delayed payout resets.

Dry run:

```bash
sudo systemctl stop vast-balance.service

sudo /opt/vast-revenue-monitor/.venv/bin/python \
  /opt/vast-revenue-monitor/balance.py \
  --config /opt/vast-revenue-monitor/config.json \
  --repair-state
```

Apply repairs:

```bash
sudo /opt/vast-revenue-monitor/.venv/bin/python \
  /opt/vast-revenue-monitor/balance.py \
  --config /opt/vast-revenue-monitor/config.json \
  --repair-state \
  --apply
```

The repair utility can rebuild:

- Hourly ATH
- Daily ATH
- Weekly ATH
- Monthly ATH

It always creates timestamped backups before modifying any state.

---

# Service Management

```bash
sudo systemctl status vast-balance.service
sudo systemctl restart vast-balance.service
sudo journalctl -u vast-balance.service -f
```

---

# Backup & Restore

Backup:

```bash
sudo /opt/vast-revenue-monitor/install.sh --backup
```

Restore:

```bash
sudo /opt/vast-revenue-monitor/install.sh --restore backup.tar.gz
```

Uninstall:

```bash
sudo /opt/vast-revenue-monitor/uninstall.sh
```

---

# Security

Never publish:

- config.json
- Discord Webhook URLs
- Vast.ai API Keys
- Backup archives
- API response dumps

Rotate both your Discord Webhook and Vast.ai API Key immediately if you suspect they have been exposed.

---

# Disclaimer

This software is provided **as-is** without warranty.

Revenue values are calculated from observed Vast.ai API data and should be treated as reference information.

Always verify important financial information against the official Vast.ai dashboard.

This software does not provide accounting, tax, investment, or financial advice.

---

# License

Released under the MIT License.
