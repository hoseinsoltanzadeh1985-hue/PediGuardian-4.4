# PediGuardian

Production track for the PediGuardian Telegram guardian platform.

## Current release
- **PediGuardian Java: 4.7.1** — archived development/emergency-recovery release artifact is tracked under `PediGuardianJava/release/`.
- **SHA-256:** `83d0f03cdf1cd8fd9b4a2a64bcac1966a5377f930aa68811d9f80da472ad6e9a`
- Java is **not** the production Telegram update owner while the Supabase webhook is active.

## Production target
- Guardian Core: Supabase Edge Function webhook
- Canonical state/RBAC: Supabase PostgreSQL
- Voice operations: separate Railway worker
- Mini Apps: game/utility frontends served over HTTPS
- Media/music: intentionally separate from Guardian Core
- Java: development/emergency recovery path

## Synchronization policy
1. GitHub is the versioned source of release artifacts and deployment documentation.
2. Supabase is the production webhook/database control plane.
3. Railway hosts persistent worker services only; it must not become a second Telegram update owner.
4. Secrets are never committed to GitHub or embedded in Mini Apps.
5. Do not run Java polling while the production Telegram webhook is active.

See `docs/RELEASE-4.7.1-SYNC.md` for the release and cross-service synchronization checklist.
