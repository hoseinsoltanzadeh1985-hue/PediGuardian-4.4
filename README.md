# PediGuardian 4.7.5 — Standard Package

A clean, importable source snapshot of PediGuardian, prepared from the validated development candidate below.

- **Source repository:** https://github.com/hoseinsoltanzadeh1985-hue/PediGuardian-4.4
- **Source ref:** `fix/4.7.5-audit-remediation`
- **Source commit:** `e4e56becb9c4038a81207d3aa919a391278c27c8`
- **Package branch:** `package/4.7.5-standard`
- **Package type:** standard deployment / self-managed infrastructure

> **Important release status:** This is a tested development package, not a production release. The source branch CI passed, but the PR is still Draft and this package has not been deployed to a live Telegram bot or production database.

## What is included

- Supabase Edge Function Telegram webhook and Telegram Bot API client.
- Supabase migrations and SQL integration tests.
- Python voice worker, Dockerfile, requirements, and worker tests.
- Telegram Bot API compatibility checker and read-only live smoke-test script.
- Backgammon rules engine and regression tests.
- Java release artifacts kept for recovery/reference only.

## Architecture

1. **Telegram updates:** one active Supabase Edge Function webhook owns Telegram updates.
2. **State and permissions:** Supabase PostgreSQL is the canonical database and authorization store.
3. **Voice worker:** a separate persistent worker runs the PyTgCalls/FFmpeg integration. The repository includes a Dockerfile under `worker/`.
4. **Mini Apps:** game interfaces are separate web applications. The included backgammon rules engine is not yet connected to a deployed game UI.
5. **Java artifacts:** do not start the legacy Java polling artifact while the Supabase webhook owns updates.

## Quick deployment checklist

1. Create or select the intended Supabase project. Confirm the project reference and inspect its existing schema and migration history before applying SQL.
2. Configure Supabase Edge Function secrets securely:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_WEBHOOK_SECRET`
   - `BOT_OWNER_ID`
   - `SUPABASE_URL`
   - `SUPABASE_SECRET_KEY` (or the supported legacy `SUPABASE_SERVICE_ROLE_KEY`)
3. Deploy the webhook and the game-center function from the matching paths in this repository. Register exactly one Telegram webhook endpoint. Do not enable a second polling process.
4. Review and apply migrations in timestamp order only after schema/RLS review and a verified backup.
5. Deploy `worker/` as a separate persistent service. Its environment template is `worker/.env.example`; set real values only in the host's protected secret/variable store.
6. Set an explicit `MEDIA_ALLOWED_HOSTS` allowlist before enabling media playback. An empty value intentionally disables playback.
7. Run the tests below, then perform controlled live tests in a private test group before any production rollout.

## Test commands

From the repository root:

```bash
node --experimental-strip-types --test cloud/supabase/functions/telegram-webhook-v4/telegram_api.test.ts
node --experimental-strip-types --test cloud/supabase/functions/game-center-v2/backgammon_engine.test.ts
python -m unittest discover -s worker -p "test_*.py" -v
python scripts/check_telegram_api_compat.py
```

The PostgreSQL integration tests require a disposable PostgreSQL 16 database:

```bash
psql -v ON_ERROR_STOP=1 -f supabase/tests/group_message_rate_limit.integration.sql
python supabase/tests/test_rate_limit_concurrency.py
```

## Current verification and limitations

- CI run #116 passed on source commit `e4e56becb9c4038a81207d3aa919a391278c27c8`.
- Telegram API unit tests, backgammon regression tests, Python worker tests, PostgreSQL integration tests, and concurrency checks passed in CI.
- The optional live Telegram smoke test was skipped because the GitHub Actions secret `TELEGRAM_BOT_TOKEN` was not configured. No live bot test is claimed.
- Captcha, complete subscription-expiry enforcement, AI provider integration, full settings write flows, backgammon Mini App wiring, Air Raider runtime, and live voice-chat verification remain incomplete or require separate validation.
- No production migration, merge, or deployment is included in this package.

## Security

Never commit bot tokens, Supabase service-role/secret keys, Telegram webhook secrets, API hashes, or user session strings. Never place privileged credentials in a Lovable/Manus browser bundle. Use platform secret stores and rotate anything that has been exposed.

See `docs/PACKAGE-STANDARD.md` for the detailed operator checklist.
