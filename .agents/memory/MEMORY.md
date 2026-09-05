# Memory Index

## User Preferences
- [user] Releasing: By default, ONLY release OTA updates. ONLY build full zips/GitHub release when user explicitly asks → release-workflow.md
- [user] Communication language: Always respond in Vietnamese (luôn trả lời bằng tiếng việt) → user-preferences.md
- [user] Handheld device: TrimUI Smart Pro / Brick (192.168.100.115) - do not reboot/kill without permission → user-preferences.md

## Project Conventions
- [project] RetroHub release workflow: 2 distinct tiers (Tier 1: OTA Update vs Tier 2: Full Installer Release) → release-workflow.md
- [project] SDL library search order: $APP/libs:/usr/trimui/lib:/usr/lib64:/usr/lib → project-conventions.md
- [project] Manifest integrity: always recalculate sha256 & size for modified files in files/ → project-conventions.md
