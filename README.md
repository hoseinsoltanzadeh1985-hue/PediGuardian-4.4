# PediGuardian 4.7.5 — canonical source

This branch is the cleaned, canonical source layout for PediGuardian 4.7.5.

- Canonical branch: `cleanup/4.7.5-canonical`
- Runtime: Supabase Edge Functions + Supabase PostgreSQL + persistent Python voice worker
- Operator UI: Lovable dashboard specification
- Optional worker host: Railway or Manus Cloud Computer
- Base application source: `fix/4.7.5-audit-remediation`
- Worker security fixes: Supabase secret-key header handling and regression tests are included.

## Architecture

1. **Telegram webhook:** Supabase Edge Function is the only owner of Telegram updates.
2. **Database:** Supabase PostgreSQL is the canonical store for groups, members, permissions, moderation state, audit events, and voice queue.
3. **Voice worker:** `worker/` contains the persistent Python worker, Dockerfile, dependency pins, and tests.
4. **Operator UI:** Lovable is a dashboard only; it must use authenticated, RLS-protected access.
5. **Hosting:** The worker can run on Railway or a persistent Manus Cloud Computer. Hosting is not provisioned by this repository.

Do not start the legacy Java polling artifact or configure a second Telegram webhook. Do not create a second database or duplicate role/queue tables.

## Repository layout

- `.github/workflows/` — current validation and Telegram API compatibility workflows
- `cloud/supabase/functions/` — Telegram webhook and game engine functions
- `supabase/migrations/` — ordered database migration history
- `supabase/tests/` — SQL and concurrency integration tests
- `worker/` — production worker source, Dockerfile, dependency pins, and regression tests
- `scripts/` — API compatibility and read-only live smoke checks
- `docs/` — deployment, architecture, Manus, and Lovable handoff documentation

Legacy Java release artifacts and 4.7.1/4.7.3/4.7.4 build workflows have been removed from this canonical branch. Historical branches and Git history remain available for recovery; they were not deleted.

## Required server-side configuration

The webhook uses these server-side variables:

- `TELEGRAM_BOT_TOKEN` (compatibility fallback: `BOT_TOKEN`)
- `TELEGRAM_WEBHOOK_SECRET`
- `BOT_OWNER_ID`
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (legacy compatibility fallback: `SUPABASE_SERVICE_ROLE_KEY`)

The worker template is `worker/.env.example`. It includes the bot token, Supabase secret, Telegram API ID/hash, user session string, and optional media allowlist. Store real values only in Railway/Manus protected environment variables or Supabase Function Secrets. Never commit secrets or paste them into chat.

## Safe rollout sequence

1. Confirm the exact existing Supabase project reference before changing secrets or deploying functions.
2. Compare all files in `supabase/migrations/` with the target database migration history and actual schema.
3. Back up a development database and apply reviewed migrations to development first.
4. Deploy the Edge Functions from this repository only after confirming migration compatibility.
5. Configure one Telegram webhook and verify it with the read-only smoke script.
6. Deploy `worker/` as one persistent service with protected variables.
7. Test in a private Telegram group and development database before production rollout.

Do not apply migrations to production until the Supabase project identity and migration history are confirmed.

## Tests

Run from the repository root:

```bash
node --experimental-strip-types --test cloud/supabase/functions/telegram-webhook-v4/telegram_api.test.ts
node --experimental-strip-types --test cloud/supabase/functions/game-center-v2/backgammon_engine.test.ts
python -m unittest discover -s worker -p "test_*.py" -v
python scripts/check_telegram_api_compat.py
```

PostgreSQL integration tests use a disposable PostgreSQL 16 instance:

```bash
psql -v ON_ERROR_STOP=1 -f supabase/tests/group_message_rate_limit.integration.sql
python supabase/tests/test_rate_limit_concurrency.py
```

## Known limitations

- Live Telegram smoke tests require a bot token secret in the CI environment; without it, that job is skipped.
- Captcha and complete subscription-expiry enforcement are not complete.
- AI provider integration and full settings write handlers are not complete.
- The backgammon engine has tests but is not fully wired to a deployed game UI.
- Air Raider UI/runtime is not verified.
- End-to-end Telegram voice-chat tests remain outstanding.
- No production migration, deployment, or merge is performed by this repository cleanup.

See `docs/PLATFORM-ARCHITECTURE.md`, `docs/MANUS-CLOUD-COMPUTER.md`, `docs/MANUS-PROMPT.md`, and `docs/LOVABLE-PROMPT.md` for deployment boundaries and handoff instructions.
