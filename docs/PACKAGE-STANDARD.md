# Standard package — operator notes

## Source identity

- Base: `fix/4.7.5-audit-remediation`
- Base commit: `e4e56becb9c4038a81207d3aa919a391278c27c8`
- Package branch: `package/4.7.5-standard`

## Deployment boundaries

This package has three runtime concerns:

| Component | Responsibility | Runtime |
|---|---|---|
| Telegram webhook | Receives Telegram updates and invokes bot logic | Supabase Edge Function |
| Database | Canonical groups, members, roles, locks, audit, and queue state | Supabase PostgreSQL |
| Voice worker | Persistent voice-chat/media queue work | Separate persistent Python service |

Only one process may own Telegram updates. Do not start the legacy Java polling artifact while the Supabase webhook is active.

## Required server-side configuration

The webhook reads these server-side variables:

- `TELEGRAM_BOT_TOKEN` (compatibility fallback: `BOT_TOKEN`)
- `TELEGRAM_WEBHOOK_SECRET`
- `BOT_OWNER_ID`
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (compatibility fallback: `SUPABASE_SERVICE_ROLE_KEY`)

The worker template is `worker/.env.example`. It includes the bot token, Supabase secret, Telegram API ID/hash, Telethon/Pyrogram user session, and optional media allowlist. Put actual values only in the hosting provider's protected secret store.

## Safe rollout order

1. Make a separate development Supabase project.
2. Compare the migration files in `supabase/migrations/` with the target's migration history, actual tables, columns, constraints, indexes, and RLS policies.
3. Back up the development database; only then apply the reviewed migrations in timestamp order.
4. Deploy the Edge Functions from the paths in `cloud/supabase/functions/` using a deployment configuration that points to this repository layout.
5. Configure one HTTPS webhook endpoint and verify it with the read-only smoke script.
6. Deploy `worker/` as a separate persistent service using its Dockerfile and protected variables.
7. Test bot updates in a private test group with limited permissions.
8. Promote only after reviewing logs, webhook ownership, RLS, moderation permissions, and voice-worker readiness.

Do not apply migrations to the operator's live Supabase project until the canonical project reference is confirmed. The source README records that the previously connected project identities need reconciliation.

## Local tests

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

## Live verification

`scripts/telegram_live_smoke.py` calls only `getMe` and `getWebhookInfo`. It confirms bot identity and the registered HTTPS webhook endpoint. It does not test all commands, group permissions, callbacks, voice chat, or game flows.

Provide `TELEGRAM_BOT_TOKEN` as an environment variable in a secure runner; never paste it into GitHub source files or chat.

## Known unfinished or unverified work

- Live bot smoke was skipped in CI because the token secret was not configured.
- Captcha and complete subscription-expiry enforcement are not complete.
- AI provider integration and full settings write handlers are not complete.
- The backgammon engine is tested but is not wired to a deployed game UI.
- Air Raider UI/runtime is not verified.
- Live Telegram voice-chat end-to-end testing is outstanding.
- No production migrations, deployment, or PR merge are included.
