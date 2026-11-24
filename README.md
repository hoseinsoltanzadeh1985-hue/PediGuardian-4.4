# PediGuardian 4.7.5 — Manus Server + Lovable UI Package

An alternative deployment package for running the persistent voice worker on a Manus Cloud Computer while building the Persian RTL management interface in Lovable.

- **Source repository:** https://github.com/hoseinsoltanzadeh1985-hue/PediGuardian-4.4
- **Source ref:** `fix/4.7.5-audit-remediation`
- **Source commit:** `e4e56becb9c4038a81207d3aa919a391278c27c8`
- **Package branch:** `package/4.7.5-manus-lovable`
- **Target arrangement:** Supabase (Telegram webhook + PostgreSQL) / Manus Cloud Computer (persistent voice worker) / Lovable (web dashboard UI)

> **Important:** This is not a completed Manus deployment or Lovable dashboard. It is the source package plus deployment instructions and build prompts. The Cloud Computer must be provisioned in your Manus account, and the Lovable UI must be generated and tested separately. No account, server, database or deployment was changed by preparing this package.

## Target architecture

1. **Supabase Edge Function:** remains the only Telegram webhook/update owner.
2. **Supabase PostgreSQL:** remains the canonical store for groups, members, roles, moderation state, audit events, and voice queue.
3. **Manus Cloud Computer:** can host the persistent Python voice worker (PyTgCalls + FFmpeg) on its Ubuntu server, using the included `worker/Dockerfile`.
4. **Lovable:** builds the responsive Persian RTL operator dashboard and connects to the confirmed Supabase project through authenticated, RLS-protected access.
5. **GitHub:** holds the source, tests, and deployment instructions.

Do not move the Telegram webhook to Manus or create another bot polling process. This prevents two services from competing for the same Telegram updates.

## What to do

1. Create a separate GitHub repository from this ZIP so your experiments remain isolated from the original repository.
2. In Manus, create/use a persistent Cloud Computer and follow `docs/MANUS-CLOUD-COMPUTER.md` to host the worker.
3. In Lovable, create the dashboard from `docs/LOVABLE-PROMPT.md`, then connect it only to the verified existing Supabase project.
4. Start with read-only group/member/role/lock/audit pages. Do not permit writes until the schema and RLS policy have been verified.
5. Test against a separate development Supabase project and a private Telegram test group before any production rollout.

## Important limitations

- The current source commit passed CI run #116, but the live Telegram smoke test was skipped because the CI token secret was not configured.
- A Cloud Computer is a persistent server resource in Manus and may have separate usage/subscription charges. Check your account's current terms before provisioning it.
- This repository does not include the generated Lovable dashboard.
- Captcha, complete subscription-expiry enforcement, AI integration, full settings writes, backgammon UI binding, Air Raider runtime, and live Telegram voice-chat tests remain incomplete or unverified.
- No production migration, merge, or deployment is included.

## Handoff documents

- `docs/MANUS-CLOUD-COMPUTER.md` — worker deployment on Manus Cloud Computer.
- `docs/MANUS-PROMPT.md` — safe Manus implementation prompt.
- `docs/LOVABLE-PROMPT.md` — Lovable dashboard prompt.
- `docs/PLATFORM-ARCHITECTURE.md` — architecture and security boundaries.
