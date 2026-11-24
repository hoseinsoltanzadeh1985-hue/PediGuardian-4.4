# Manus Server + Lovable UI — PediGuardian architecture

## Goal

Use a persistent Manus Cloud Computer for the existing voice worker and use Lovable to build the operator dashboard, without changing the Telegram webhook owner or creating a second database.

## System map

```text
Telegram users/groups
       |
       v
Telegram Bot API
       |
       v
Supabase Edge Function  <---- sole Telegram webhook/update owner
       |
       +----> Supabase PostgreSQL (canonical state, RLS, audit)
       |
       +----> voice queue
                  |
                  v
        Manus Cloud Computer
        Python worker + PyTgCalls + FFmpeg
        persistent process; outbound Supabase connection

Lovable: Persian RTL admin UI
       |
       +----> authenticated, RLS-protected Supabase access
GitHub: source, CI, tests, version history
```

## Responsibilities

### Supabase

Keep the current webhook, database, privileged RPCs, authorization, and queue here. The bot token, webhook secret, and Supabase secret remain server-side. Use exactly one Telegram webhook and do not start legacy Java polling while the webhook is active.

### Manus Cloud Computer

The worker in `worker/` is a persistent Python service. The included Dockerfile installs Python dependencies and FFmpeg. A Manus Cloud Computer is a persistent Ubuntu server intended to keep applications and bots running outside active Manus sessions. Use it as the worker host only after confirming the account has this resource and reviewing its current charges.

The worker connects outbound to Supabase to claim queue work and write heartbeats. Its HTTP health endpoint listens on port 8787 by default. Keep that port private unless there is a clear monitoring requirement and a firewall rule that restricts access.

### Lovable

Build the dashboard UI, not a second bot. Connect it to the confirmed Supabase project using public/publishable client credentials and authenticated RLS-protected reads. Do not expose service-role/secret keys, bot tokens, webhook secrets, Telegram API hashes, or user session strings. Start read-only.

## Dashboard access model

Before enabling any browser data access, verify the actual production schema and RLS. If current policies do not allow safe authenticated reads, do not relax them. Instead propose narrowly scoped server-side RPCs/views for review. Authorization for every write must be enforced by the database/server and audited; hiding a button is not authorization.

## What this package does not do

- It does not deploy or provision a Manus Cloud Computer.
- It does not create a Lovable project or dashboard automatically.
- It does not move the Telegram webhook off Supabase.
- It does not apply database migrations or change production secrets.
- It does not certify live Telegram group, voice-chat, or game functionality.

