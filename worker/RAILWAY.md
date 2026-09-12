# PediGuardian Voice Worker — Railway 24/7

This service is intentionally voice-only. It does not own Telegram bot updates and must never run polling for the Guardian bot.

Required Railway variables (set as secrets):
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `TG_API_ID`
- `TG_API_HASH`
- `TG_SESSION_STRING` (or `TG_USER_SESSION`)
- `BOT_TOKEN`

Non-secret defaults:
- `WORKER_ID` optional
- `HEARTBEAT_SECONDS=10`
- `PORT` supplied by Railway when available; default `8787`

Security: never commit the MTProto session string or Bot token to GitHub. The worker reads them only from Railway environment variables.

Runtime contract:
- current Voice Chat roster only
- no historical weighting
- no monetary/betting mechanics
- Supabase `claim_voice_order_request` is the only job-claim RPC
- `/health` returns the worker health payload
