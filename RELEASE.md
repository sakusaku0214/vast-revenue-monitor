# Vast Revenue Monitor v1.0.1

This maintenance release fixes fresh installation failure caused by
`NOTIFICATION_LANGUAGE` being referenced before it was assigned. Interactive
installs now prompt for English or Japanese after the report-detail question;
non-interactive installs default safely to English or validate an explicit `en`
or `ja`. Existing configuration, revenue behavior, state, and operations remain
unchanged.
