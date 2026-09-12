# PediGuardian

Production track for the PediGuardian Telegram guardian platform.

## Current target
- Guardian Core: Supabase Edge Function webhook
- Canonical state/RBAC: Supabase PostgreSQL
- Voice operations: separate Railway worker
- Mini Apps: Air Raider, Backgammon, and current voice-roster selection wheel
- Media/music: intentionally separate from Guardian Core
- Java: development/emergency recovery path, not the production Telegram update owner

## Security model
Telegram is authoritative for current membership/admin permissions. Supabase stores canonical application state and configuration. Production webhook processing is single-owner/idempotent.

## Release source
The repository is being initialized from the validated 4.7 production build. Secrets are never committed.
