# Simorgh / PediGuardian 4.7.1

This release is a cleanup/fix pass based on the Termux + Telegram audit from 2026-09-12.

## Verified problems and fixes

- Local Java 4.7.0 was receiving commands; the core poller was not the cause of the apparent dead bot.
- Telegram Webhook was empty during local testing, so Local mode is now explicitly treated as polling/recovery mode.
- Game Center previously relied on a Supabase Edge Function to serve HTML. Supabase documents Edge Functions as API/runtime endpoints and notes that `text/html` responses can be rewritten to `text/plain`, which explains the raw HTML screen.
- Static Mini Apps were added under `games/` and are intended to be served through GitHub/jsDelivr.
- Both Air Raider and Backgammon are now always present in the 4.7.1 Java Game Center defaults.
- Added direct `/airraider` and `/backgammon` commands.
- Added `/wheel` as an alias for `/voiceorder`.
- Added `/report`, `/reports`, `/note`, `/notes`, `/config` handlers.
- Removed the dead `/purge` menu item from the admin command menu.
- Voice queue now resolves internal `groups.id` from `telegram_chat_id` before writing a `voice_order_requests` row.
- Help and branding strings were updated from stale 4.4 wording.
- Polling logs now show when Telegram update batches are received.

## Security rules retained

- Telegram native membership/administrator state is checked before privileged actions.
- Bot Owner and Group Owner remain distinct.
- Target hierarchy protects Bot Owner and Group Owner accounts.
- Bot/API secrets remain environment-only.
- Voice selection is a non-monetary, current-Voice-Chat roster utility with no weighting/history.

## AI

The provider gateway remains environment-driven. Current upstream verification confirms `openai/gpt-oss-120b` is a supported Groq production model, `gemini-3.7-flash` is a current stable Gemini model, and OpenAI supports the `gpt-5.6` alias through the Responses API.
