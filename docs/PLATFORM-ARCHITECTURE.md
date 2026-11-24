# Manus + Lovable integration architecture

## Goal

Create an operator dashboard and optional web control panel without replacing the existing Telegram bot backend or introducing a second source of truth.

## System boundaries

```text
Telegram users and groups
          |
          v
Telegram Bot API
          |
          v
Supabase Edge Function  <---- exactly one Telegram webhook owner
          |
          +------> Supabase PostgreSQL (canonical state + RLS)
          |
          +------> queued voice work
                          |
                          v
                 Persistent voice worker
                 (Python + PyTgCalls + FFmpeg)

Manus: build/review the operator portal or auxiliary web app
Lovable: build the responsive Persian RTL UI and connect to the
         already-confirmed Supabase project through safe access paths
GitHub: versioned code, CI, review, and package source
```

## Responsibilities

### Existing Supabase backend

Keep the webhook, database, access-control checks, and privileged RPCs here unless a separately reviewed migration changes the architecture. The webhook must keep its bot token, webhook secret, and Supabase secret on the server.

### Voice worker

Keep it on a persistent host that supports the included Dockerfile, Python dependencies, FFmpeg, PyTgCalls, HTTPS health checks, and protected environment variables. Do not assume a static frontend host can run this worker.

### Manus

Use Manus to inspect this repository and generate an operator portal or supporting web application. Manus can build and publish web applications, but do not let it create a competing Telegram webhook, an independent role database, or a second copy of production records.

### Lovable

Use Lovable for UI generation and preview. Connect it to the existing Supabase project only after the canonical project reference is confirmed. The frontend must use public/publishable credentials and authenticated RLS-protected access. Never put privileged secrets in browser code.

## Dashboard access policy

Start with a read-only dashboard. Before enabling writes:

1. Inspect the real production schema and RLS.
2. Define which authenticated dashboard users may see which groups.
3. Implement narrowly scoped server-side RPCs for required writes.
4. Enforce authorization in the database/server, not by hiding buttons.
5. Add audit events for every privileged action.
6. Add tests for owner/admin boundaries, cross-group isolation, and revoked roles.

Do not guess column names from the UI, and do not relax RLS to make a page work.

## Deployment gates

- Use a separate development Supabase project and private Telegram test group.
- Keep exactly one active webhook for the bot.
- Verify bot identity and webhook URL with the non-mutating smoke test.
- Verify database migrations and RLS before any writes.
- Verify the voice worker's readiness and queue lease behavior.
- Test group commands and callbacks with test accounts.
- Do not deploy or migrate production until an explicit release review has passed.

## What is not included in this package

There is no completed Manus portal or Lovable frontend in the repository. These are build instructions for creating them as separate projects. The Telegram bot runtime and voice worker remain separate server-side services.
