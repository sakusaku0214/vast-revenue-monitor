# Vast Revenue Monitor v1.1.0

This accounting release confirms delayed weekly resets only on a real balance drop, adds Yesterday, assigns monthly revenue from completed weekly closings, restricts ATHs to completed periods (except Hourly), provides an explicit backed-up repair workflow, and adds the safe `sudo ./update.sh` production updater. Existing event arrays remain readable; new metadata is additive, while repair is never run automatically.
