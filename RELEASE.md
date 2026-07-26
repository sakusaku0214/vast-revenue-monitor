# Vast Revenue Monitor v1.0.1

This hotfix prevents fresh installations from referencing `NOTIFICATION_LANGUAGE` before it is assigned. Interactive first installs now select English or Japanese after the Weekly Goal and Detailed Report questions, defaulting to English on Enter. Unattended installs accept `en` or `ja` and safely default to English when the variable is unset. Upgrades continue preserving existing configuration without a language prompt.
