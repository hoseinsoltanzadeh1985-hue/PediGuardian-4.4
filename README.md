# PediGuardian 4.7.5 — Manus + Lovable Package

A platform-integration package for building a web control panel around the existing PediGuardian Telegram backend.

- **Source repository:** https://github.com/hoseinsoltanzadeh1985-hue/PediGuardian-4.4
- **Source ref:** `fix/4.7.5-audit-remediation`
- **Source commit:** `e4e56becb9c4038a81207d3aa919a391278c27c8`
- **Package branch:** `package/4.7.5-manus-lovable`
- **Target workflow:** Manus for assisted full-stack/dashboard work; Lovable for the responsive Persian RTL operator UI; existing Supabase remains the canonical bot backend.

> **Important:** This repository does not contain a finished React/Lovable dashboard, and it is not a one-click Manus deployment package. It contains the existing bot backend plus an integration brief and ready-to-use prompts. The dashboard must be generated and then tested against the real schema and RLS policies.

## Recommended separation of responsibilities

- **Telegram bot runtime:** keep the current Supabase Edge Function as the single Telegram webhook owner.
- **Database and access control:** keep the confirmed Supabase project as the single source of truth. Do not create a parallel database or duplicate permission system in Manus/Lovable.
- **Persistent voice worker:** keep the separate worker on a persistent host that supports Python, FFmpeg, PyTgCalls, health checks, and protected environment variables. The included worker Dockerfile is the starting point.
- **Manus:** use it to build/review the operator portal or auxiliary full-stack web app and to help deploy that portal. Do not ask it to replace the Telegram webhook or silently migrate production data.
- **Lovable:** use it to build the responsive UI and connect it to the existing Supabase project. Its browser code must use only the public/publishable key and authenticated, RLS-protected access.
- **GitHub:** keep code and review history here. Treat this package branch as a snapshot, not as the live production deployment.

## Why this split matters

The bot webhook uses server-side credentials and handles Telegram updates. A browser dashboard must never receive the Telegram bot token, Supabase secret/service-role key, Telegram API hash, or user session string. Lovable supports connecting an app to Supabase and using its database and Edge Functions; Manus supports building and publishing web apps. Those platform features do not mean that this existing webhook/worker can be deployed unchanged as a frontend-only project.

## Recommended workflow

1. Import this ZIP into a **new GitHub repository** so experiments do not affect the original source repository.
2. In Manus, connect that new repository and ask it to inspect the code and create an operator dashboard only. Use the prompt in `docs/MANUS-PROMPT.md`.
3. In Lovable, create the UI project and connect the already-confirmed Supabase backend. Use `docs/LOVABLE-PROMPT.md`.
4. Start with read-only pages (group profile, members/roles, locks, audit history, worker health). Do not enable database writes until every table, column, RPC, authentication rule, and RLS policy has been checked.
5. Keep the webhook and voice worker on their existing server-side deployment paths. Do not let Manus/Lovable create a second Telegram webhook or duplicate the bot's update polling.
6. Test with a separate Supabase development project and private Telegram test group. Promote only after explicit review and live smoke tests.

## Current verification and limitations

- Source commit `e4e56becb9c4038a81207d3aa919a391278c27c8` passed CI run #116.
- The source package has no completed Lovable dashboard or Manus WebDev application yet.
- Live Telegram smoke testing was skipped because the CI token secret was absent.
- Production DB schema/RLS, live voice-chat, bot commands, subscription expiry, Captcha, AI, and game UI integrations are not certified as production-ready.
- No production deployment, database migration, PR merge, or credential transfer was performed.

## Files for platform handoff

- `docs/MANUS-PROMPT.md` — scoped Manus build prompt and guardrails.
- `docs/LOVABLE-PROMPT.md` — Lovable UI prompt with Persian RTL and security requirements.
- `docs/PLATFORM-ARCHITECTURE.md` — responsibility map and deployment gates.
- `worker/.env.example` — names of voice-worker variables; use real values only in protected platform settings.

See `docs/PLATFORM-ARCHITECTURE.md` before connecting any live service.
