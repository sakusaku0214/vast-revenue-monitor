# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-07-26

### Added

- Hourly Discord revenue reports with USD and JPY values, compact and detailed
  display modes, weekly-goal progress, all-time highs, and separate record embeds.
- Correct latest-successful-interval Hourly accounting without rolling-window
  double counting or rate extrapolation.
- English and Japanese Discord notifications, install-time language selection, and
  safe post-install language and Weekly Goal reconfiguration.
- Complete English and Japanese operator documentation.
- Vast.ai current-user balance polling with query-key authentication, retry logic,
  strict response validation, and redacted API diagnostics.
- Persistent positive-balance-delta accumulation for latest-interval, 09:00 JST
  business-day, Saturday 09:00 JST weekly, and monthly revenue calculations.
- Saturday reset handling that archives the last observed weekly balance and counts
  the first post-reset balance from zero.
- Three-provider USD/JPY failover with a persistent last-known-good cache.
- Persistent JSON records, atomic state writes, yearly CSV history rotation, daily
  goal calculations, and adaptive weekly-reset state.
- Status-based Discord embed colors, all-GPU-available warnings, and Vast.ai schema
  change alerts.
- Daily gzip-compressed log rotation with 30-day retention.
- Transactional Ubuntu 24.04 installer with interactive credential and weekly-goal
  configuration, upstream validation, rollback, and hardened systemd deployment.
- Reconfiguration, private backup, safely validated restore, complete uninstall,
  and backup-before-uninstall workflows.
- Safe backup extraction with path confinement, entry-type checks, file-count and
  expanded-size limits, configuration validation, and restore rollback.
- Comprehensive pytest coverage and GitHub Actions checks for pytest and ShellCheck.
- Installation, configuration, troubleshooting, backup, restore, upgrade, complete
  uninstall, and end-to-end host verification documentation.

### Security

- Run the service as a dedicated non-login user with systemd sandboxing and a
  restrictive umask.
- Keep application code root-owned while limiting service writes to state and log
  directories.
- Store configuration, state, diagnostics, and backup archives with restrictive
  permissions.
- Redact API keys, contact details, SSH keys, Discord identifiers, and HMAC values
  from persisted Vast.ai diagnostics.
- Reject unsafe backup paths, links, devices, FIFOs, oversized archives, and
  excessive archive entries before restoration.
