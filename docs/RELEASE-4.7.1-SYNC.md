# PediGuardian 4.7.1 — Release & Cross-Service Sync Handbook

## Scope

This document records the safe synchronization boundary for the 4.7.1 Java release across GitHub, Supabase, and Railway.

## 1. GitHub

- Release artifact: `PediGuardianJava/release/pedi-guardian-java-4.7.1.jar`
- Source archive: `PediGuardianJava/source/PediGuardianJava-4.7.1-source.zip`
- SHA-256: `83d0f03cdf1cd8fd9b4a2a64bcac1966a5377f930aa68811d9f80da472ad6e9a`
- Secrets must never be committed.

## 2. Supabase

Production project: `PediGuardian` (`ygzabgsyfehmlaarphpx`).

The active Edge Function `telegram-webhook-v47` is the cloud Telegram update path. The Java 4.7.1 artifact must not be treated as a second update owner while this webhook is active.

Before declaring a cloud release synchronized, verify:

- `telegram-webhook-v47` is ACTIVE.
- The deployed function code version and repository source agree.
- Required server-side secrets exist: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `BOT_OWNER_ID`, `SUPABASE_SERVICE_ROLE_KEY`.
- Database migrations required by the function exist and are compatible.
- RLS remains enabled for protected application tables.

## 3. Railway

Production project: `PediGuardian-4.4`.

The Railway service named `PediGuardian-VoiceWorker-4.7.1` is a separate worker. It must not receive or own Telegram bot updates.

Required worker configuration is server-side only. Never place `TG_SESSION_STRING`, `TG_API_HASH`, or other secrets in GitHub or chat.

Before declaring the worker synchronized, verify:

- Source repository and `worker` root directory both exist.
- Dockerfile builds successfully.
- `/health` becomes healthy.
- Restart policy is enabled.
- Supabase connectivity and worker heartbeat are healthy.
- The worker is not configured as a second Telegram Bot polling/webhook owner.

## 4. Rollout order

1. Verify GitHub artifact and checksum.
2. Verify Supabase production function/database state.
3. Verify Railway worker build and health.
4. Only then switch any production routing.
5. Keep rollback artifacts available.

## 5. Rollback rule

Do not delete additive database migrations to roll back an application. Revert the application/function deployment to the last verified release and keep compatible schema objects in place.

## 6. Current known gap

At the time this handbook was created, the Railway `PediGuardian-VoiceWorker-4.7.1` service had a failed deployment and its configured source pointed at the repository `worker` directory. The current GitHub repository tree must therefore be checked before retrying that deployment. No secret values are recorded here.
