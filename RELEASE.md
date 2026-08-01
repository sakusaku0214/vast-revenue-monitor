# Vast Revenue Monitor v1.1.1

This accounting consistency release calculates Today from the balance at the JST 09:00 boundary, keeps Yesterday fixed, and defines payout weeks as Saturday 09:00-to-Saturday 09:00. A payout month contains the four or five completed payout weeks assigned to it plus its current running week. Hourly ATH updates immediately; Daily, Weekly, and Monthly ATHs use completed periods only. The explicit, backup-first repair command can detect and rebuild invalid completed-period ATHs, but no repair is ever applied automatically.
