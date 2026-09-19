# Memory Index

## User Preferences
- [user] Releasing: By default, ONLY release OTA updates. ONLY build full zips/GitHub release when user explicitly asks → release-workflow.md
- [user] OTA Notification: Always send release notification to the Telegram general topic (-1003890413445) upon OTA release → release-workflow.md
- [user] Communication language: Always respond in Vietnamese (luôn trả lời bằng tiếng việt) → user-preferences.md
- [user] Handheld device: TrimUI Smart Pro / Brick (192.168.100.115) - do not reboot/kill without permission → user-preferences.md

## Project Conventions
- [project] RetroHub release workflow: 2 distinct tiers (Tier 1: OTA Update vs Tier 2: Full Installer Release) → release-workflow.md
- [project] SDL library search order: $APP/libs:/usr/trimui/lib:/usr/lib64:/usr/lib → project-conventions.md
- [project] Manifest integrity: always recalculate sha256 & size for modified files in files/ → project-conventions.md
- [project] UI button text: no icons/emojis in buttons or UI text to prevent font glyph glitches → project-conventions.md
- [project] UI text anti-overlap rules: width budgeting, auto-ellipsis with max_w, concise control values, and no bilingual cramming → project-conventions.md

