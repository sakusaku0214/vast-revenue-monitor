# Changelog

## v1.1.4 (unpublished)

- Attribute each daily revenue increment to the JST business day containing its interval start, so the final pre-09:00 interval completes Yesterday and Today begins at zero at exactly 09:00.
- Rebuild Daily ATH from the corrected completed-day attribution during explicit state repair while preserving the event-state format and backup-first apply behavior.

## v1.1.3

- Fix payout-month rollover so first-Saturday reset confirmations finalize the previous payout month, restart This month from the new running week, and update Monthly ATH only from completed payout-month evidence.
- Extend explicit state repair coverage for missing or invalid Monthly ATH values rebuilt from persisted weekly closures.

## v1.1.2

- Resolve relative state and log directories from the configuration file location, independent of the caller's working directory.
- Rebuild Hourly ATH from corrected positive interval increments during explicit state repair.

## v1.1.1

- Define Today and Yesterday on JST 09:00 boundaries and calculate Today from the balance at that boundary rather than displaying the cumulative balance.
- Define payout weeks as Saturday 09:00-to-Saturday 09:00 and payout months as four or five completed payout weeks plus the current running week.
- Rename the record panel to ATH and restrict Daily, Weekly, and Monthly ATHs to completed periods; extend explicit state repair to rebuild invalid ATH data.

## v1.1.0

- Confirm delayed Vast.ai weekly resets with an observed balance drop.
- Add 09:00 business-day Yesterday reporting and completed-period ATH semantics.
- Derive months from completed weekly closings.
- Add dry-run/apply state repair with backups and a safe one-command updater.

## v1.0.1

- Fixed fresh installation failure when `NOTIFICATION_LANGUAGE` was referenced before assignment.
- Added first-install English/Japanese selection with a safe English unattended default.
- Preserved existing language configuration without prompting during upgrades.

## v1.0.0

- Corrected Hourly to report only the latest successful interval increment.
- Added safe post-install Weekly Goal and language reconfiguration.
- Added English and Japanese Discord notifications and post-install switching.
- Added complete English and Japanese operator documentation.
