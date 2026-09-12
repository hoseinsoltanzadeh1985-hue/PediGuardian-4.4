# Serverless Live Snapshot — 4.7.0

Source artifact recorded locally:

- `PediGuardian-4.7.0-live-sync.zip`
- SHA-256: `52cb6ef6e4473c18448653ce64ba7329da0eb324f876d74abe24e02e6b617b0c`

## What the snapshot contains

- Supabase Edge webhook track
- PostgreSQL migration track
- Java recovery controller source/JAR
- Voice Worker source
- Air Raider Mini App
- Backgammon Mini App
- deployment and checksum files

## Reconciliation status

This is a source snapshot, not an assertion that every file can be promoted unchanged to production.

Known reconciliation items:

1. The live `telegram_updates` table stores `update_id`/timestamps only; an older snapshot migration expects a `payload` column.
2. The canonical live group settings model is `groups.settings`; older Cloud code may still reference `group_settings`.
3. Production Telegram Update ownership must be exactly one path: Cloud webhook or Java polling.
4. Mini Apps must be served from HTTPS static hosting rather than relying on an Edge Function to return HTML.
5. Railway Voice Worker is not currently deployed with its required variables; user-session credentials must stay in Railway secrets and never in Git.

This document exists so future releases do not silently repeat the earlier schema/ownership drift.
