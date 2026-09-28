# Simorgh Mini Games

Static HTTPS Mini Apps for the Guardian bot.

Supabase Edge Functions remain the API/runtime layer. The game pages are static files in this repository and are served through GitHub/jsDelivr so Telegram receives real HTML/JavaScript instead of an Edge Function response that can be rewritten as `text/plain`.

## URLs for release 4.7.1

- `games/index.html`
- `games/air-raider/index.html`
- `games/backgammon/index.html`

Release code uses the immutable jsDelivr base:

`https://cdn.jsdelivr.net/gh/hoseinsoltanzadeh1985-hue/PediGuardian-4.4@6f3ee56a18e9ff0599f0ae5ceb70bd7e5ef7ab04/games`

The games are entertainment only and contain no betting or monetary mechanics.
