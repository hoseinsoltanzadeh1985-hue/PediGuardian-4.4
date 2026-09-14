# PediGuardian 4.7.1 — Release & Cross-Service Sync Handbook

## Scope

This document records the safe synchronization boundary for the 4.7.1 Java release across GitHub, Supabase, and Railway, including the multi-winner Voice Wheel utility.

## 1. GitHub

- Java release artifact: `PediGuardianJava/release/pedi-guardian-java-4.7.1.jar`
- Java source archive: `PediGuardianJava/source/PediGuardianJava-4.7.1-source.zip`
- Java 4.7.1 SHA-256: `83d0f03cdf1cd8fd9b4a2a64bcac1966a5377f930aa68811d9f80da472ad6e9a`
- Voice worker source: `worker/worker.py`
- Voice worker Dockerfile: `worker/Dockerfile`
- Secrets must never be committed.

## 2. Supabase

Production project: `PediGuardian` (`ygzabgsyfehmlaarphpx`).

The active Edge Function `telegram-webhook-v47` is the cloud Telegram update path. The Java 4.7.1 artifact must not be treated as a second update owner while this webhook is active.

For the Voice Wheel queue, `voice_order_requests.group_id` is the internal `groups.id` FK. The worker must resolve that FK to `groups.telegram_chat_id` before calling Telegram MTProto APIs. This distinction is mandatory.

The multi-winner release raises the queue `count` constraint to 1..200. The wheel itself stops at the effective roster size, so it can never select more people than the current snapshot.

Before declaring a cloud release synchronized, verify:

- `telegram-webhook-v47` is ACTIVE.
- The deployed function code version and repository source agree.
- Required server-side secrets exist: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `BOT_OWNER_ID`, `SUPABASE_SERVICE_ROLE_KEY`.
- Required database migrations exist and are compatible.
- RLS remains enabled for protected application tables.
- `voice_order_requests_count_check` is `count >= 1 AND count <= 200`.
- `voice_presence_group_observed_idx` exists.

## 3. Railway

Production project: `PediGuardian-4.4`.

The Railway service named `PediGuardian-VoiceWorker-4.7.1` is a separate worker. It must not receive or own Telegram bot updates.

The repository now contains the configured `worker/` root with a Dockerfile. The worker is voice-only and consumes the Supabase queue; it does not call `getUpdates` or set a Bot API webhook.

Required worker configuration is server-side only. Never place `TG_SESSION_STRING`, `TG_API_HASH`, or other secrets in GitHub or chat.

Required environment values are the existing server-side secrets plus `VOICE_WHEEL_URL` pointing to the verified HTTPS GitHub Pages wheel URL. The default source value is the Simorgh Pages path, but production should be verified before relying on it.

Before declaring the worker synchronized, verify:

- `worker/worker.py` and `worker/Dockerfile` are present.
- Dockerfile builds successfully.
- `/health` becomes healthy.
- Restart policy is enabled.
- Supabase connectivity and worker heartbeat are healthy.
- The worker resolves `groups.id` to the real Telegram `telegram_chat_id`.
- Current voice roster is read at request execution time only.
- Winner selection is performed by the Mini App without attendance weighting or history weighting.
- The worker sends the roster/count launcher once; the Mini App performs the sequential elimination spins.
- The worker is not configured as a second Telegram Bot polling/webhook owner.

## 4. Voice Wheel behavior

- Admin/authorized command supplies the requested selection count.
- The worker snapshots only users present in the active voice chat at execution time.
- The wheel displays `Name (@username)` when a username exists; otherwise `Name` only.
- One participant is selected per spin using a uniform random choice among remaining participants.
- The selected participant is enlarged in the winner card, recorded in the winner list, and removed from the wheel before the next spin.
- The process continues until the requested number of winners is reached or the roster is empty.
- The static page uses URL-fragment payload transport for roster data so the static host does not receive it as an HTTP query.
- The static page is presentation/game logic, not an authorization boundary. Authorization remains in the bot/worker path.

## 5. Rollout order

1. Verify GitHub artifacts and source.
2. Verify the Supabase schema/migration state.
3. Verify the GitHub Pages wheel deployment and HTTPS URL.
4. Deploy/restart the Railway worker and verify `/health` + heartbeat.
5. Issue one controlled test request in a test group with 2–3 current voice participants.
6. Verify winners are unique, displayed correctly, and excluded from subsequent spins.
7. Only then switch any production routing.
8. Keep rollback artifacts available.

## 6. Rollback rule

Do not delete additive database migrations to roll back an application. Revert the application/function deployment to the last verified release and keep compatible schema objects in place.

## 7. Current known gap

The database migration and repository worker source are now prepared. A production synchronization is not considered complete until the Railway deployment succeeds and the GitHub Pages wheel URL is verified in Telegram. No secret values are recorded here.
