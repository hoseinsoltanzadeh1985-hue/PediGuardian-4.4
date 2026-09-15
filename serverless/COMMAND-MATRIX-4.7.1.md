# Simorgh / PediGuardian 4.7.1 — Command Engine Matrix

Goal: every visible command must map to a real engine/handler or be removed from the BotFather menu. No dead menu entries.

## Engine ownership

| Engine | Responsibility |
|---|---|
| GeneralHandler | start, help, version, id, profile, language, rules, status |
| ModerationHandler | warn, warnings, clearwarnings, setwarninglimit, mute, unmute, ban, unban, kick, del, pin, unpin |
| SecurityHandler | lock, unlock, locks, security, antiraid, admins, addadmin, removeadmin, grantperm, revokeperm, perms, logs, settings, setrules, welcome, setwelcome, filter, filters, badword, badwords, settag |
| FeatureHandler | ai, aistatus, game, emoji, voiceorder |
| OwnerHandler | groups, extend, trial |
| GameCenter | Air Raider, Backgammon, game launcher |
| VoiceOrderQueue | current Voice Chat roster selection requests |
| AiService | provider gateway and fallback state |
| GroupAccessStore | 15-day access/trial and extension state |

## Required command surface

`/start /help /version /id /profile /language /rules /status /panel`

`/warn /warnings /clearwarnings /setwarninglimit /mute /unmute /ban /unban /kick /del /pin /unpin`

`/lock /unlock /locks /security /antiraid /admins /addadmin /removeadmin /grantperm /revokeperm /perms /logs /settings /setrules /welcome /setwelcome /filter /filters /badword /badwords /settag`

`/ai /aistatus /game /emoji /voiceorder /wheel`

`/groups /extend /trial`

`/airraider /backgammon`

## Aliases

Persian aliases must resolve to the same handler as the English command. Alias resolution must not bypass authorization, native Telegram permission checks, access checks, rate limiting, or audit logging.

## Release gate

Before production promotion, CI/test scripts must verify:

1. Every BotFather command resolves to a handler.
2. Every callback used by Glass Panel resolves to a callback action.
3. Privileged actions perform current Telegram-native permission checks.
4. Group ownership and Bot Owner authority are distinct.
5. Demoted/removed Telegram admins cannot retain privileged access through stale DB state.
6. `groups.id` is used for internal foreign keys; `groups.telegram_chat_id` is used for Telegram API calls.
7. The production Telegram update owner is exactly one of Cloud webhook or local polling, never both.
8. Game URLs are HTTPS static pages and do not rely on returning HTML from a Supabase Edge Function.
9. Voice wheel selects only the current Voice Chat roster; no betting, money, history or attendance weighting.
10. Secrets are never committed to source control.
