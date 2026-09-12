"""PediGuardian Voice Worker: current Voice Chat roster only; no history or weighting."""
from __future__ import annotations

import asyncio
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
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
WORKER_ID = os.getenv("WORKER_ID", f"voice-worker-{os.getpid()}")
HEARTBEAT_SECONDS = max(3, int(os.getenv("HEARTBEAT_SECONDS", "10")))
PORT = int(os.getenv("PORT", "8787"))
TG_API_ID = os.getenv("TG_API_ID")
TG_API_HASH = os.getenv("TG_API_HASH")
TG_SESSION_STRING = os.getenv("TG_SESSION_STRING") or os.getenv("TG_USER_SESSION")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")


def headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def request(method: str, url: str, **kwargs):
    last = None
    for attempt in range(3):
        try:
            response = requests.request(method, url, timeout=15, **kwargs)
            response.raise_for_status()
            return response
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(2**attempt + random.random())
    raise RuntimeError(f"request failed: {last}")


class Store:
    def __init__(self):
        self.base = f"{SUPABASE_URL}/rest/v1"

    def pending(self):
        return request(
            "GET",
            f"{self.base}/voice_order_requests?status=eq.PENDING&order=created_at.asc&limit=20",
            headers=headers(),
        ).json()

    def claim(self, request_id: int) -> bool:
        response = request(
            "POST",
            f"{SUPABASE_URL}/rest/v1/rpc/claim_voice_order_request",
            headers=headers(),
            json={"p_id": request_id, "p_worker_id": WORKER_ID},
        )
        return response.text.strip().lower() in {"true", "[true]"}

    def group_chat_id(self, group_id: int) -> int:
        rows = request(
            "GET",
            f"{self.base}/groups?id=eq.{group_id}&select=telegram_chat_id&limit=1",
            headers=headers(),
        ).json()
        if not rows:
            raise RuntimeError(f"unknown group_id {group_id}")
        return int(rows[0]["telegram_chat_id"])

    def complete(self, request_id: int, status: str, result: dict):
        request(
            "PATCH",
            f"{self.base}/voice_order_requests?id=eq.{request_id}",
            headers=headers(),
            json={
                "status": status,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "result": result,
            },
        )

    def heartbeat(self):
        request(
            "POST",
            f"{self.base}/voice_worker_heartbeats",
            headers={**headers(), "Prefer": "resolution=merge-duplicates"},
            json={
                "worker_id": WORKER_ID,
                "status": "IDLE",
                "details": {"version": "4.7.1", "mode": "voice-only"},
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
            },
        )


class VoiceClient:
    def __init__(self):
        self.client = (
            Client(
                WORKER_ID,
                api_id=int(TG_API_ID),
                api_hash=TG_API_HASH,
                session_string=TG_SESSION_STRING,
            )
            if Client and raw and TG_API_ID and TG_API_HASH and TG_SESSION_STRING
            else None
        )

    async def start(self):
        if not self.client:
            raise RuntimeError("TG_API_ID/TG_API_HASH/TG_SESSION_STRING are required")
        await self.client.start()

    async def close(self):
        if self.client:
            try:
                await self.client.stop()
            except Exception:
                pass

    async def participants(self, chat_id: int):
        peer = await self.client.resolve_peer(chat_id)
        call = None
        if hasattr(peer, "channel_id"):
            full = await self.client.invoke(
                raw.functions.channels.GetFullChannel(
                    channel=raw.types.InputChannel(
                        channel_id=peer.channel_id, access_hash=peer.access_hash
                    )
                )
            )
            call = getattr(full.full_chat, "call", None)
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
            more = await self.client.invoke(
                raw.functions.phone.GetGroupParticipants(
                    call=call, ids=[], sources=[], offset=offset, limit=100
                )
            )
            parts.extend(getattr(more, "participants", []) or [])
            users.update({int(u.id): u for u in (getattr(more, "users", []) or [])})
            offset = getattr(more, "next_offset", "") or ""

        out = []
        seen = set()
        for participant in parts:
            if getattr(participant, "left", False):
                continue
            peer_obj = getattr(participant, "peer", None)
            user_id = getattr(peer_obj, "user_id", None)
            if user_id is None or int(user_id) in seen:
                continue
            user_id = int(user_id)
            seen.add(user_id)
            user = users.get(user_id)
            username = getattr(user, "username", None) if user else None
            name = (
                f"@{username}" if username else ""
            ) or (
                (f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}").strip()
                if user
                else ""
            ) or str(user_id)
            out.append({"id": user_id, "name": name})
        return out

    async def notify(self, chat_id: int, text: str):
        if not BOT_TOKEN:
            raise RuntimeError("BOT_TOKEN is required for result notification")
        request(
            "POST",
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )


async def main():
    store = Store()
    voice = VoiceClient()
    await voice.start()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    try:
        while not stop.is_set():
            try:
                store.heartbeat()
            except Exception:
                LOG.exception("heartbeat failed")

            for item in store.pending():
                request_id = int(item["id"])
                try:
                    if not store.claim(request_id):
                        continue
                    chat_id = store.group_chat_id(int(item["group_id"]))
                    count = max(1, min(20, int(item.get("count", 1))))
                    people = await voice.participants(chat_id)
                    if not people:
                        raise RuntimeError("در این لحظه فردی در ویس‌کال حاضر نیست.")
                    random.SystemRandom().shuffle(people)
                    chosen = people[:count]
                    await voice.notify(
                        chat_id,
                        "🎙️ نوبت ویس‌کال\n\n"
                        + "\n".join(f"{i}. {p['name']}" for i, p in enumerate(chosen, 1))
                        + "\n\nفقط وضعیت لحظه اجرای درخواست لحاظ شد.",
                    )
                    store.complete(
                        request_id,
                        "DONE",
                        {
                            "mode": "CURRENT_ROSTER",
                            "count": len(chosen),
                            "users": [p["id"] for p in chosen],
                        },
                    )
                except Exception as exc:
                    LOG.exception("voice request %s failed", request_id)
                    try:
                        store.complete(request_id, "FAILED", {"error": str(exc)[:500]})
                    except Exception:
                        LOG.exception("failed to mark request %s as FAILED", request_id)

            try:
                await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                pass
    finally:
        await voice.close()


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b'{"ok":true,"version":"4.7.1","mode":"voice-only"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


def serve():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), HealthHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    serve()
    asyncio.run(main())
