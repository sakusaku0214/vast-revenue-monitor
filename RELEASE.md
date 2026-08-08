# Vast Revenue Monitor v1.1.4

This hotfix corrects daily revenue attribution at the JST 09:00 boundary. Each observed increment represents the interval from the previous successful sample through the current sample and is assigned to the business day containing that interval's start. Consequently, an interval ending exactly at 09:00 completes Yesterday, Today is exactly $0.00 at rollover, and the interval starting at 09:00 is the first revenue added to Today.

Daily ATH now uses the corrected completed 09:00-to-09:00 total. Explicit backup-first state repair can detect and correct a Daily ATH produced by the old end-timestamp attribution using the existing persisted event evidence. Latest interval, weekly and payout-month accounting, and non-daily ATH behavior are unchanged.
