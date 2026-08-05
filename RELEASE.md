# Vast Revenue Monitor v1.1.3

This hotfix corrects payout-month rollover accounting. Completed payout weeks are rebuilt from persisted weekly reset evidence, the running week is assigned to the month of its next Saturday closing boundary, and a first-Saturday payout reset finalizes the previous payout month instead of carrying prior completed weeks into the new month. After rollover, This month starts from the new running payout week, while Monthly ATH updates only from completed payout-month totals.

The release also extends explicit backup-first state repair so `--repair-state` can detect and repair missing or invalid Monthly ATH values, including `0.00`, when completed payout-month evidence exists. Existing Today, Yesterday, This week, Hourly ATH, Daily ATH, and Weekly ATH behavior remains unchanged.
