# Lovable prompt — PediGuardian Persian RTL dashboard

Build a separate responsive web dashboard for the existing PediGuardian Telegram bot. The dashboard is a user interface only; preserve the current Telegram webhook and backend architecture.

## Read these files first

- `README.md`
- `docs/PLATFORM-ARCHITECTURE.md`
- `supabase/README.md`
- SQL migrations under `supabase/migrations/`

## Non-negotiable safety constraints

- Connect only to the intended existing Supabase project after its project reference is confirmed.
- Do not create another bot database, duplicate roles, or a second Telegram webhook.
- Do not expose Telegram bot tokens, webhook secrets, Supabase secret/service-role keys, Telegram API hashes, or user session strings to the browser.
- Use only the Supabase publishable/anon key in client configuration; all data access must be protected by Supabase Auth and RLS.
- Never disable RLS, add broad public policies, or place privileged SQL credentials in frontend code.
- Do not invent tables, columns, RPCs, or permissions. Inspect the migrations and the actual schema first.
- If secure read access is not available under current RLS, build the UI against typed mock fixtures clearly labelled as development-only and report the exact server-side change required. Do not weaken security to make the UI appear functional.

## UI requirements

Create a polished Persian-first, right-to-left dashboard with a language toggle for English. Use a consistent component system and responsive layouts for mobile and desktop.

Pages:
1. Overview — verified service health and factual summary cards.
2. Groups — list and group details.
3. Members — members, status, and role hierarchy.
4. Moderation — warning history and lock status.
5. Audit — searchable audit events.
6. Voice worker — health/readiness from an authenticated or otherwise trusted status endpoint.
7. Settings — read-only until secure write RPCs are specified and approved.

Use explicit states for loading, no data, denied access, stale status, and network failure. Never hardcode "Online" or use fabricated counts.

## Data and authorization

- Propose the authentication flow before coding.
- Map each page to the real table/view/RPC it uses.
- Apply least-privilege RLS for each user and group.
- Enforce all writes in the database or server-side functions; UI-only permission checks are insufficient.
- Add audit logging for approved privileged changes.
- Do not implement destructive operations in the initial read-only milestone.

## Engineering

Use TypeScript, strict types, reusable components, and tests. Keep environment configuration in platform secrets/settings. Add a README showing how to connect the approved Supabase project and how to run the preview.

## Deliverables

A working preview plus a data-access map, an RLS/authorization report, tests, and a list of features that remain unimplemented. Do not claim the Telegram bot is live just because the dashboard preview works.
