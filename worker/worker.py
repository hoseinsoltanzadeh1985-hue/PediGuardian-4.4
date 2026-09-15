"""PediGuardian 4.7.1 voice-only worker.

The worker owns no Telegram Bot updates. It consumes a Supabase queue, resolves the
internal group FK to the real Telegram chat id, snapshots the current voice-call
roster, and posts a one-time Telegram Mini App launcher containing that roster.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import random
import signal
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import requests

try:
    from pyrogram import Client, raw
except Exception:  # pragma: no cover
    Client = None
    raw = None

LOG = logging.getLogger("pedi.voice_worker")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
# Current project naming is SUPABASE_SECRET_KEY; retain compatibility with the
# legacy SUPABASE_SERVICE_ROLE_KEY name used by older worker revisions.
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_SECRET_KEY (or legacy SUPABASE_SERVICE_ROLE_KEY) is required")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
VOICE_WHEEL_URL = os.getenv(
    "VOICE_WHEEL_URL",
    "https://hoseinsoltanzadeh1985-hue.github.io/Simorgh/games/voice-wheel.html",
).strip()
WORKER_ID = os.getenv("WORKER_ID", f"voice-worker-{os.getpid()}")
HEARTBEAT_SECONDS = max(3, int(os.getenv("HEARTBEAT_SECONDS", "10")))
PORT = int(os.getenv("PORT", "8787"))
MAX_ROSTER = max(1, min(200, int(os.getenv("MAX_ROSTER", "200"))))
TG_API_ID = os.getenv("TG_API_ID")
TG_API_HASH = os.getenv("TG_API_HASH")
TG_SESSION_STRING = os.getenv("TG_SESSION_STRING") or os.getenv("TG_USER_SESSION")


def headers() -> dict[str, str]:
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}


def request(method: str, url: str, **kwargs) -> requests.Response:
    last = None
    for n in range(3):
        try:
            response = requests.request(method, url, timeout=15, **kwargs)
            response.raise_for_status()
            return response
        except Exception as exc:
            last = exc
            if n < 2:
                time.sleep(2**n + random.random())
    raise RuntimeError(f"request failed: {last}")


def encode_payload(payload: dict) -> str:
    raw_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")


class Store:
    def __init__(self) -> None:
        self.base = f"{SUPABASE_URL}/rest/v1"

    def pending(self) -> list[dict]:
        return request("GET", f"{self.base}/voice_order_requests?status=eq.PENDING&order=created_at.asc&limit=20", headers=headers()).json()

    def claim(self, request_id: int) -> bool:
        response = request("POST", f"{SUPABASE_URL}/rest/v1/rpc/claim_voice_order_request", headers=headers(), json={"p_id": request_id, "p_worker_id": WORKER_ID})
        return response.text.strip().lower() in {"true", "[true]"}

    def complete(self, request_id: int, status: str, result: dict) -> None:
        request("PATCH", f"{self.base}/voice_order_requests?id=eq.{request_id}", headers=headers(), json={"status": status, "completed_at": datetime.now(timezone.utc).isoformat(), "result": result})

    def heartbeat(self) -> None:
        request(
            "POST",
            f"{self.base}/voice_worker_heartbeats?on_conflict=worker_id",
            headers={**headers(), "Prefer": "resolution=merge-duplicates"},
            json={"worker_id": WORKER_ID, "status": "IDLE", "details": {"version": "4.7.1", "mode": "voice-only", "roster": "current-at-execution", "wheel": "multi-winner-elimination"}, "last_seen_at": datetime.now(timezone.utc).isoformat()},
        )

    def group_chat_id(self, group_id: int) -> int:
        rows = request("GET", f"{self.base}/groups?id=eq.{group_id}&select=telegram_chat_id&limit=1", headers=headers()).json()
        if not rows or rows[0].get("telegram_chat_id") is None:
            raise RuntimeError(f"group {group_id} has no telegram_chat_id")
        return int(rows[0]["telegram_chat_id"])

    def snapshot(self, group_id: int, people: list[dict]) -> None:
        rows = [{"group_id": group_id, "user_id": int(p["id"]), "display_name": p["display_name"]} for p in people]
        if rows:
            request("POST", f"{self.base}/voice_call_presence_snapshots", headers={**headers(), "Prefer": "return=minimal"}, json=rows)


class VoiceClient:
    def __init__(self) -> None:
        self.client = None
        if Client and raw and TG_API_ID and TG_API_HASH and TG_SESSION_STRING:
            self.client = Client(WORKER_ID, api_id=int(TG_API_ID), api_hash=TG_API_HASH, session_string=TG_SESSION_STRING)

    async def start(self) -> None:
        if not self.client:
            raise RuntimeError("TG_API_ID/TG_API_HASH/TG_SESSION_STRING are required")
        await self.client.start()

    async def close(self) -> None:
        if self.client:
            try:
                await self.client.stop()
            except Exception:
                pass

    async def participants(self, chat_id: int) -> list[dict]:
        peer = await self.client.resolve_peer(chat_id)
        if hasattr(peer, "channel_id"):
            full = await self.client.invoke(raw.functions.channels.GetFullChannel(channel=raw.types.InputChannel(channel_id=peer.channel_id, access_hash=peer.access_hash)))
        else:
            full = await self.client.invoke(raw.functions.messages.GetFullChat(chat_id=chat_id))
        call = getattr(full.full_chat, "call", None)
        if not call:
            return []
        page = await self.client.invoke(raw.functions.phone.GetGroupCall(call=call, limit=100))
        parts = list(getattr(page, "participants", []) or [])
        users = {int(u.id): u for u in (getattr(page, "users", []) or [])}
        offset = getattr(page, "participants_next_offset", "") or ""
        while offset:
            more = await self.client.invoke(raw.functions.phone.GetGroupParticipants(call=call, ids=[], sources=[], offset=offset, limit=100))
            parts.extend(getattr(more, "participants", []) or [])
            users.update({int(u.id): u for u in (getattr(more, "users", []) or [])})
            offset = getattr(more, "next_offset", "") or ""
        out: list[dict] = []
        seen: set[int] = set()
        for participant in parts:
            if getattr(participant, "left", False):
                continue
            peer_obj = getattr(participant, "peer", None)
            uid = getattr(peer_obj, "user_id", None)
            if uid is None or int(uid) in seen:
                continue
            uid = int(uid)
            seen.add(uid)
            user = users.get(uid)
            username = getattr(user, "username", None) if user else None
            first = (getattr(user, "first_name", "") or "") if user else ""
            last = (getattr(user, "last_name", "") or "") if user else ""
            display = f"{first} {last}".strip() or (f"@{username}" if username else str(uid))
            out.append({"id": uid, "username": username or "", "display_name": display})
            if len(out) >= MAX_ROSTER:
                break
        return out


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in {"/health", "/heartbeat"}:
            self.send_response(404); self.end_headers(); return
        body = b'{"ok":true,"mode":"voice-only","roster":"current-at-execution","wheel":"multi-winner"}'
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *_args) -> None:
        return


def serve() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HealthHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server


async def notify(chat_id: int, people: list[dict], count: int) -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required for wheel notification")
    users = [{"id": p["id"], "name": p["display_name"], "username": p["username"]} for p in people]
    winners = min(max(1, int(count)), len(users))
    wheel_url = f"{VOICE_WHEEL_URL}?count={winners}#data={encode_payload({'users': users})}"
    payload = {
        "chat_id": chat_id,
        "text": "🎡 <b>گردونه ویس‌کال سیمرغ</b>\n\n" + f"👥 حاضرین همین لحظه: <b>{len(users)}</b>\n" + f"🏆 تعداد انتخاب: <b>{winners}</b>\n" + "هر برنده بعد از هر چرخش از گردونه حذف می‌شود.",
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": [[{"text": "🎡 اجرای گردونه", "web_app": {"url": wheel_url}}]]},
    }
    request("POST", f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)


async def main() -> None:
    store = Store(); voice = VoiceClient(); await voice.start()
    stop = asyncio.Event(); loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    try:
        while not stop.is_set():
            store.heartbeat()
            for command in store.pending():
                request_id = int(command["id"])
                if not store.claim(request_id):
                    continue
                group_id = int(command["group_id"])
                requested = max(1, min(MAX_ROSTER, int(command.get("count") or 1)))
                try:
                    chat_id = store.group_chat_id(group_id)
                    people = await voice.participants(chat_id)
                    if not people:
                        raise RuntimeError("در این لحظه فردی در ویس‌کال حاضر نیست.")
                    chosen_count = min(requested, len(people))
                    store.snapshot(group_id, people)
                    await notify(chat_id, people, chosen_count)
                    result_users = [{"id": p["id"], "username": p["username"], "name": p["display_name"]} for p in people]
                    store.complete(request_id, "DONE", {"mode": "CURRENT_ROSTER", "requested_count": requested, "effective_count": chosen_count, "count": len(people), "users": result_users, "wheel": "multi-winner-elimination"})
                except Exception as exc:
                    LOG.exception("voice request %s failed", request_id)
                    store.complete(request_id, "FAILED", {"error": str(exc)[:500]})
            try:
                await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                pass
    finally:
        await voice.close()


if __name__ == "__main__":
    serve(); asyncio.run(main())
