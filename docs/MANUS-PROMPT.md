# Manus prompt — host PediGuardian voice worker on Cloud Computer

Inspect the repository and read `README.md`, `docs/PLATFORM-ARCHITECTURE.md`, and this file before doing anything.

## Goal

Use my existing Manus Cloud Computer as the persistent host for the Python voice worker in `worker/`. Do not rebuild the Telegram bot or move its webhook.

## Mandatory boundaries

1. Keep the Supabase Edge Function as the only Telegram webhook/update owner.
2. Keep Supabase PostgreSQL as the canonical database and queue.
3. Do not start the legacy Java polling artifact.
4. Do not create a second Telegram bot, a second webhook, a second queue, or duplicate role tables.
5. Do not run database migrations or modify production data.
6. Never commit or print credentials. Never put bot tokens, Supabase secret/service-role keys, Telegram API hashes, or user session strings in GitHub, logs, prompts, browser code, or screenshots.
7. Do not expose port 8787 to the public internet by default.

## Steps

1. Check whether a Manus Cloud Computer already exists and is active. If none exists, explain that provisioning may incur a separate charge and ask me before creating or purchasing anything.
2. Confirm available OS, CPU/RAM/disk, Docker availability, outbound network access to the selected Supabase project, and the process supervisor available.
3. Inspect `worker/Dockerfile`, `worker/requirements.txt`, `worker/worker.py`, and `worker/.env.example`. Confirm the Docker build context is `worker/`.
4. Prepare a protected environment file outside the Git working tree. Ask me to enter required values through the server's secure environment mechanism; never ask me to paste secrets into chat or commit them.
5. Build the included worker image from `worker/`. If Docker is unavailable, propose a Python 3.11 + FFmpeg + virtual-environment + systemd alternative and show the exact commands before running them.
6. Run the worker under a restart-on-failure policy. Keep port 8787 bound to localhost unless I explicitly approve a restricted external health-check route.
7. Verify logs without printing secret values. Verify `/health` locally, worker readiness, Supabase heartbeat, and queue claim/release behavior in a development project.
8. Report the actual host status, resource usage, service restart policy, and exact tests completed. Do not call it production-ready unless live test evidence supports that claim.

## After worker setup

Prepare a deployment note for Lovable. The Lovable frontend must connect to the same confirmed Supabase project through authenticated RLS-safe access. It must never connect directly using service-role credentials.
