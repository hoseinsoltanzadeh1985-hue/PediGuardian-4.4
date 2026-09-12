# PediGuardian / Simorgh — Serverless Release Track

This directory preserves the serverless production architecture alongside the Java recovery controller.

## Runtime ownership

- Telegram Bot API updates: Supabase Edge Function only.
- PostgreSQL: canonical group/RBAC/config/audit state.
- Supabase Queue/RPC: background jobs.
- Railway: voice-only MTProto worker; never a second Telegram Bot API update owner.
- Mini Apps: HTTPS static hosting for Air Raider and Backgammon.
- Java/Termux: development and emergency recovery only.

## Important rule

Never run Java polling and the production webhook for the same bot token at the same time.

## Current live project

Supabase project ref: `ygzabgsyfehmlaarphpx`

Existing production functions and worker are maintained separately from the Java recovery package.

## Included design

```text
Telegram
   |
   v
Supabase Edge Webhook
   |
   +--> PostgreSQL (groups, members, access, locks, warnings, audit)
   +--> Command/Panel/Game dispatch
   +--> Voice job queue
              |
              v
       Railway Voice Worker
              |
              v
       MTProto current roster

Mini Apps -> HTTPS static hosting
Music/Media -> separate service
```

## Security boundary

Secrets belong only in platform secret stores/environment variables. Do not commit bot tokens, webhook secrets, Supabase server keys, AI provider keys, or Telegram user-session strings.

This snapshot is intentionally a release-track reference. Production deployment must be validated against the live schema and current secrets before promotion.
