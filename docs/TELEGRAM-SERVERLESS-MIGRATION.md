# Telegram Serverless Migration — Working Plan

**Status:** preparation only. This branch is not deployed and does not own the production webhook.

## Objective

Move the Simorgh/PediGuardian bot core to Telegram Serverless in a controlled migration, while preserving the existing production path until a separate test bot proves the new handlers and data model.

## Target responsibilities

| Component | Responsibility after migration |
|---|---|
| Telegram Serverless | Sole Telegram Bot API update owner; commands, group security, RBAC, callbacks, and bot-side Mini App endpoints |
| Telegram Serverless SQLite | Primary state for migrated bot features: groups, membership, roles, warnings, locks, settings, audit events, and update idempotency |
| Telegram-hosted Mini App | Admin interface and game/tool front ends served with the bot |
| Railway | Voice/MTProto worker only, if still needed; never a second Bot API polling or webhook owner |
| Supabase | Existing production data plane during transition; any long-term bridge must use a documented server-side secret mechanism and least-privilege credentials |
| GitHub | Versioned source, migration review, CI and release artifacts |
| Notion | Architecture decisions, runbooks, acceptance-test evidence and release notes |
| Adalo | Defer unless a separate native mobile management app is still required; the Telegram-hosted Mini App should be evaluated first |

## Important platform constraints

1. Telegram Serverless modules use the platform SDK for the Bot API, SQLite and outbound HTTP. Runtime modules are not ordinary Node.js/Deno processes and must not assume filesystem access, npm packages or arbitrary environment-variable access.
2. The documented Serverless runtime does not currently describe a general-purpose secret manager or runtime environment-variable interface. Therefore, **do not place a Supabase service-role key, Telegram bot token, worker session or any other credential in the source tree or Mini App**. A Supabase bridge is blocked until a supported secret-delivery mechanism is verified.
3. The SQLite database is per bot and does not enforce foreign keys. Relationships must be enforced by application code and tested explicitly.
4. Code deployment and schema migration are separate operations. Review the schema diff before applying migrations.
5. A full Serverless push mirrors the deployed module set. Deleting a local module can delete it from the deployed module set. Keep the production bot disconnected from this branch during development.
6. Serverless manages the bot webhook. Do not run a second polling process and do not execute webhook synchronization against the production bot during development.

## Migration sequence

### Phase 0 — Baseline and safety

- Keep the current Supabase webhook and production bot unchanged.
- Verify the deployed webhook owner and pending-update state immediately before any future cutover.
- Reconcile the deployed Edge Function source with the GitHub source.
- Export and checksum the selected data before any schema or runtime migration.
- Keep the existing Java artifact and the last known-good webhook path available for rollback.

### Phase 1 — Isolated Serverless implementation

- Use the post-CLI-0.2.0 layout: `tgcloud/handlers`, `tgcloud/endpoints`, `tgcloud/lib`, and `tgcloud/schema.js`.
- Separate handlers by update type: messages, callback queries, membership changes and other required update types.
- Centralize authorization checks in a shared RBAC module.
- Model explicit role grants separately from native Telegram administrator rights. App-level demotion cannot revoke native Telegram rights; those must be changed through Telegram itself.
- Add idempotency and bounded retry/outbox behavior before implementing side effects.
- Use a dedicated test bot for platform-level tests. Do not link this project to the production bot during this phase.

### Phase 2 — State migration

- Map only required tables and fields; do not blindly copy all Postgres tables.
- Use Telegram chat/user identifiers as stable external identifiers.
- Rebuild relational integrity in application code because SQLite foreign keys are unavailable in this runtime.
- Reconcile counts and key records before and after import.
- Preserve an export of the original Supabase data and migration mapping.

### Phase 3 — Mini App

- Prefer the Telegram-hosted Mini App and Serverless endpoints for the bot's own admin interface.
- Let the platform validate Mini App `initData` for Serverless endpoints; never treat client-supplied role labels or user IDs as authorization.
- Keep all permission checks in server-side handlers/endpoints.
- Use the hosted app for panels and games; do not expose service credentials to the front end.

### Phase 4 — Voice worker

- Keep the Railway worker independent and voice-only where MTProto/Pyrogram session access is required.
- Define a narrow authenticated queue contract only after secure secret injection from Serverless has been established.
- Verify worker heartbeats, queue claiming, duplicate-request behavior and group-ID mapping before enabling voice features.

### Phase 5 — Production cutover

Cut over only after all acceptance tests pass on the test bot. A cutover must have a single update owner at every moment:

1. Freeze production changes and record the current webhook state.
2. Take a verified data export and record the rollback target.
3. Deploy and test the Serverless modules and schema against the test bot.
4. Perform a planned handover of webhook ownership; never leave polling and webhook runtimes competing.
5. Verify `/start`, commands, callbacks, group security, role revocation, persistence, logs and Mini App authorization.
6. Keep the prior webhook implementation and data export ready for rollback.

## Acceptance tests

- Duplicate `update_id` does not repeat a side effect.
- A failed operation can be safely retried without duplicate messages/actions.
- Member access is denied for privileged commands.
- Role hierarchy prevents lower roles from granting or changing higher roles.
- Removing an app-level role takes effect on the next request.
- Native Telegram permissions are checked separately from app roles.
- Stale or forged callback data cannot perform a privileged action.
- Locks, warnings and filters are enforced on ordinary messages, not merely stored as settings.
- Callback navigation invokes real handlers or clearly reports that a feature is unavailable.
- Every security status displayed in the UI is derived from actual checks.
- State survives cold starts and deployment.
- Mini App endpoints reject invalid or stale Telegram initialization data.
- A Supabase or Railway outage does not break unrelated core commands.
- The Serverless webhook's allowed update types match the deployed handlers.

## Current blockers

- The existing main branch and the deployed Supabase webhook are not yet a verified one-to-one release pair.
- The current Java 4.7.4 pull request is separate from the production branch; its latest observed build attempt failed while fetching its external 4.7.1 source archive, before compilation.
- The repository does not contain a complete, reproducible set of Supabase SQL migration files.
- A supported way to provide external-service secrets to Telegram Serverless modules must be verified before any service-role Supabase integration is attempted.

## Useful first-party references

- Telegram Serverless: https://core.telegram.org/bots/serverless
- Telegram Mini Apps: https://core.telegram.org/bots/webapps
- Telegram Bot API changelog: https://core.telegram.org/bots/api-changelog
