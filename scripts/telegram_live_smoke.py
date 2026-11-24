#!/usr/bin/env python3
"""Non-mutating live smoke checks for Telegram bot identity and webhook ownership."""
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def call(token: str, method: str) -> dict:
    request = Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Telegram {method} returned HTTP {exc.code}") from None
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Telegram {method} smoke check failed: {type(exc).__name__}") from None
    if not payload.get("ok"):
        code = payload.get("error_code", "unknown")
        raise RuntimeError(f"Telegram {method} rejected the request (code {code})")
    return payload.get("result") or {}


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN is not configured", file=sys.stderr)
        return 2

    try:
        me = call(token, "getMe")
        if me.get("is_bot") is not True or not me.get("id"):
            raise RuntimeError("getMe did not return a valid bot identity")
        print(f"PASS: getMe identifies a bot (id={me['id']}, username=@{me.get('username', 'unknown')})")

        info = call(token, "getWebhookInfo")
        url = info.get("url", "")
        if not url:
            raise RuntimeError("No webhook is registered; expected the single Supabase webhook owner")
        if not url.startswith("https://") or "telegram-webhook" not in url:
            raise RuntimeError("Registered webhook URL is not an HTTPS PediGuardian Telegram webhook endpoint")
        pending = info.get("pending_update_count", 0)
        print(f"PASS: HTTPS Telegram webhook is registered; pending updates={pending}")
        if info.get("last_error_date"):
            print("WARNING: Telegram reports a recent webhook delivery error; inspect getWebhookInfo in the operator console.")
        print("PASS: read-only live Telegram smoke checks completed; no group messages or moderation actions were sent.")
        return 0
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
