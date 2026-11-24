# PediGuardian

**Current development release: PediGuardian 4.7.5**

PediGuardian is a Telegram group guardian platform. This repository is the versioned source of truth for the bot, its webhook, worker, Mini Apps, migrations, and release documentation.

> **Release status (2026-11-24):** 4.7.5 is the latest validated development candidate on `fix/4.7.5-production-hardening`. Its CI checks pass. It is not yet promoted to `main` or deployed to production. Promotion is gated on the production Supabase project/schema being confirmed, Railway secrets being configured, and the game UI/live Telegram smoke tests being completed.

## Architecture

- **Guardian Core:** Supabase Edge Functions receive Telegram updates. Keep exactly one production Telegram update owner.
- **Canonical state and authorization:** Supabase PostgreSQL, including group membership, role hierarchy, permissions, audit records, and durable queues.
- **Persistent voice worker:** Railway runs the separate PediGuardian voice worker. Railway must not become a second Telegram update poller/webhook owner.
- **Mini Apps:** HTTPS-hosted Telegram Web Apps for games and utilities.
- **Game engine:** The 4.7.5 branch includes a deterministic TypeScript backgammon rules engine and regression tests. The rules engine still needs integration into the deployed Backgammon Mini App and end-to-end testing.
- **Java artifact:** PediGuardian Java 4.7.1 is retained as a development/emergency-recovery artifact; it is not the production update owner while the Supabase webhook is active.
- **Media scope:** Voice playback is restricted to media sources the operator is authorized to use. Explicit HTTPS host allowlisting and redirect validation are required.

## 4.7.5 changes

- Webhook inbox idempotency with per-update UUID leases and safe retry behavior.
- Group message lock enforcement for links, media, voice, and documents, subject to Telegram delete permissions.
- Actor/target role-hierarchy checks and Telegram-native permission checks for moderation.
- Read-only detail views for members, roles, locks, audit events, security permissions, group profile, and settings.
- Database migrations for group/member/access/audit/voice data, queue leases, member fields, and webhook inbox.
- Voice queue claims use unique UUID lease tokens; only the current lease holder can complete a job.
- Voice worker play/pause/resume/stop dispatch using PyTgCalls, with FFmpeg, explicit HTTPS media allowlisting, and redirect validation.
- Separate liveness/readiness behavior; stale worker heartbeats fail readiness.
- Deterministic backgammon engine covering bar entry, hits, blocking, bearing off, doubles, mandatory dice usage, and winner detection.

## Verification

Latest recorded CI run for the 4.7.5 candidate: **GitHub Actions run #77 — successful**.

- Deno Edge Function checks
- Strict TypeScript type-check for the backgammon engine
- Node.js backgammon regression suite
- 24 Python worker tests
- Source/schema contract checks

CI success is not a substitute for production verification. Live Telegram group voice-chat tests, multiplayer game end-to-end tests, and production schema/RLS verification remain required.

## Telegram compatibility and automatic maintenance

- A dedicated Telegram Bot API client is isolated from the webhook handler and covered by unit tests for successful responses, Telegram API errors, HTTP failures, malformed responses, invalid method names, network failures, and secret redaction.
- A scheduled weekly compatibility workflow compares every Bot API method used by the webhook with the official Telegram Bot API documentation.
- When `TELEGRAM_BOT_TOKEN` is configured as a GitHub Actions secret, the scheduled workflow also performs non-mutating live checks with `getMe` and `getWebhookInfo`. It does not send group messages or execute moderation actions.
- Dependabot proposes weekly updates for Python worker dependencies and GitHub Actions. Proposed updates must pass CI and review before merge; production code is never replaced automatically by an unverified dependency update.
- The PostgreSQL flood-control migration has SQL integration tests for configured limits, per-user/per-group isolation, privilege restrictions, RLS enablement, and concurrent requests.

## Expanded verification

The validation workflow now runs the Telegram API client unit suite, existing backgammon rules regression suite, Python worker tests, and a PostgreSQL service-backed integration suite for the atomic flood limiter. Scheduled Telegram compatibility checks run separately from pull-request CI.

## Production release gates

Before promoting 4.7.5 to `main` or deploying it:

1. Confirm the single canonical Supabase project. The project URL currently documented by the operator is `https://csjmancduvajisunvggs.supabase.co`; the connected Supabase integration has also shown a different project reference. Do not apply migrations until the discrepancy is resolved.
2. Verify production migration history, tables, constraints, indexes, and RLS policies against the branch migrations.
3. Configure Railway's protected Variables for the voice worker. Required names include:
   - `SUPABASE_URL`
   - `SUPABASE_SECRET_KEY` (or the supported legacy `SUPABASE_SERVICE_ROLE_KEY`)
   - `BOT_TOKEN`
   - `TG_API_ID`
   - `TG_API_HASH`
   - `TG_SESSION_STRING` (or supported `TG_USER_SESSION`)
   - `MEDIA_ALLOWED_HOSTS` (only approved HTTPS media hosts; an empty allowlist intentionally disables playback)
   - Any deployment-specific worker variables documented in `worker/`.
4. Keep secrets out of Git, README files, Mini Apps, issue comments, and chat. Add them only through Railway's protected Variables UI. Rotate any secret that was exposed outside a secure secret manager.
5. Integrate and test the backgammon engine in the deployed Mini App. Client-submitted scores are not authoritative until server-side match state and score validation exist.
6. Run controlled Telegram webhook, moderation, queue-lease, voice-worker, and game smoke tests.
7. Promote to `main` and deploy only after the above gates pass.

## Deployment ownership policy

- GitHub is the versioned source of code and release documentation.
- Supabase is the production webhook/database control plane.
- Railway hosts persistent worker services only.
- Do not run Java polling while the production Telegram webhook is active.
- Do not deploy a second Telegram update owner.
- Never commit service-role or secret API keys.
