# Manus build prompt — PediGuardian operator portal

You are extending an existing Telegram moderation bot repository. First inspect the entire repository and read this file plus `docs/PLATFORM-ARCHITECTURE.md` and `README.md`.

## Goal

Build a separate, responsive operator/admin portal for PediGuardian 4.7.5. This portal is a management UI; it is not a replacement Telegram bot runtime.

## Mandatory architecture constraints

1. Keep the existing Supabase Edge Function as the only Telegram webhook/update owner.
2. Keep the existing Supabase project as the canonical bot database after its project reference is confirmed.
3. Do not migrate the Telegram bot webhook to Manus, create a second polling process, or create duplicate groups/members/roles tables.
4. Do not change existing migrations or production data without explicit approval.
5. Do not put `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `SUPABASE_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, Telegram API hashes, or user session strings in browser code, client env variables, source control, or logs.
6. Never bypass or disable Supabase RLS. Never trust a hidden UI button as authorization.
7. Do not invent schema fields, RPC names, or existing capabilities. Inspect migrations and, when available, the actual development database schema first. Report anything that cannot be verified.

## First milestone — read-only

Build Persian-first RTL pages with a clean responsive layout:

- Overview: service status, counts only where the source data supports them.
- Groups: group list and basic profile.
- Members and roles: view-only hierarchy and member status.
- Moderation: warnings, locks, and audit history as read-only screens.
- Voice worker: liveness/readiness information only when a trusted endpoint exists.
- Settings: read-only display until safe write APIs are approved.

Include English labels as a secondary language. Make empty, loading, permission-denied, and network-error states explicit. Do not display fabricated online indicators or mock production data as real.

## Data access and authentication

- Propose an authentication model before implementing access.
- Use only public/publishable Supabase credentials on the client.
- Read data only through authenticated, RLS-protected access or narrowly scoped server-side endpoints.
- If current RLS does not support secure dashboard reads, stop and report the exact missing policies/API boundary. Do not weaken RLS.
- All privileged actions, if later approved, must be enforced server-side and recorded in the existing audit model.

## Quality requirements

- TypeScript with strict checks.
- Responsive mobile layout and Persian RTL text.
- Accessibility for keyboard navigation and contrast.
- No secret values in source maps, browser bundles, console logs, or network responses.
- Add tests for authorization boundaries and UI error states.
- Document every assumed integration and distinguish tested features from placeholders.

## Deliverables

1. A working development preview of the read-only portal.
2. A schema/access map identifying every table, view, or RPC used.
3. A list of missing RLS policies or endpoints; do not silently create them.
4. Automated tests and a concise test report.
5. Deployment instructions separated from production release instructions.

Before publishing or connecting a live project, show the target project, variables required, security impact, and proposed changes. Wait for approval before production deployment.
