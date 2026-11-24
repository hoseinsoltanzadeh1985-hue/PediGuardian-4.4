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
import ipaddress
import socket
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import requests

try:
    from pyrogram import Client, raw
except Exception:  # pragma: no cover
    Client = None
    raw = None

try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import AudioQuality, MediaStream
except Exception:  # pragma: no cover
    PyTgCalls = None
    AudioQuality = None
    MediaStream = None

LOG = logging.getLogger("pedi.voice_worker")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
# New sb_secret keys are opaque API keys, not JWTs. Legacy service_role keys
# are JWTs and may also be sent as Authorization: Bearer.
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_KEY = SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY

# Readiness is separate from liveness: Railway must not mark a worker healthy
# until the MTProto client starts and the first Supabase heartbeat succeeds.
READY = False

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
MEDIA_ALLOWED_HOSTS = {value.strip().lower().rstrip(".") for value in os.getenv("MEDIA_ALLOWED_HOSTS", "").split(",") if value.strip()}
LAST_HEARTBEAT = 0.0


def validate_environment() -> None:
    """Fail fast with variable names only; never print credential values."""
    missing: list[str] = []
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        missing.append("SUPABASE_SECRET_KEY (or SUPABASE_SERVICE_ROLE_KEY)")
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not TG_API_ID:
        missing.append("TG_API_ID")
    else:
        try:
            if int(TG_API_ID) <= 0:
                raise ValueError("must be positive")
        except (TypeError, ValueError):
            raise RuntimeError("TG_API_ID must be a positive integer")
    if not TG_API_HASH:
        missing.append("TG_API_HASH")
    if not TG_SESSION_STRING:
        missing.append("TG_SESSION_STRING (or TG_USER_SESSION)")
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))


def safe_source(source: str) -> bool:
    """Accept HTTPS media only from an explicit allowlist and public DNS addresses."""
    try:
        parsed = urlparse(source)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port or len(source) > 2048:
            return False
        if not host or not MEDIA_ALLOWED_HOSTS:
            return False
        if not any(host == allowed or host.endswith("." + allowed) for allowed in MEDIA_ALLOWED_HOSTS):
            return False
        if host == "localhost" or host.endswith(".localhost"):
            return False
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        if not addresses:
            return False
        return all(
            (ip := ipaddress.ip_address(address)).is_global
            and not ip.is_private and not ip.is_loopback
            and not ip.is_link_local and not ip.is_reserved
            for address in addresses
        )
    except (OSError, ValueError):
        return False


def resolve_safe_source(source: str) -> str:
    """Validate every redirect destination before handing the URL to FFmpeg."""
    current = source
    for _ in range(6):
        if not safe_source(current):
            raise RuntimeError("stream source must be a public HTTPS URL on an allowlisted host")
        response = requests.get(
            current, headers={"Range": "bytes=0-0"}, allow_redirects=False,
            stream=True, timeout=(5, 10),
        )
        try:
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                if not location:
                    raise RuntimeError("media redirect has no Location header")
                current = urljoin(current, location)
                continue
            if response.status_code not in {200, 206}:
                raise RuntimeError("media source did not return a stream response")
            return current
        finally:
            response.close()
    raise RuntimeError("media source redirect limit exceeded")


def headers() -> dict[str, str]:
    result = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    # Supabase's new sb_secret_* keys must NOT be sent as Bearer tokens.
    if not SUPABASE_SECRET_KEY and SUPABASE_SERVICE_ROLE_KEY:
        result["Authorization"] = f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"
    return result


def request(method: str, url: str, *, retry_safe: bool = False, **kwargs) -> requests.Response:
    """Retry only operations explicitly marked idempotent and never expose token-bearing URLs."""
    last: Exception | None = None
    attempts = 3 if retry_safe else 1
    for attempt in range(attempts):
        try:
            response = requests.request(method, url, timeout=15, **kwargs)
            response.raise_for_status()
            return response
        except Exception as exc:
            last = exc
            if attempt < attempts - 1:
                time.sleep(2**attempt)
    error_type = type(last).__name__ if last is not None else "UnknownError"
    raise RuntimeError(f"{method} request failed after {attempts} attempt(s): {error_type}") from None


def encode_payload(payload: dict) -> str:
    raw_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")


class Store:
    def __init__(self) -> None:
        self.base = f"{SUPABASE_URL}/rest/v1"

    def reclaim_expired(self) -> None:
        request(
            "POST",
            f"{SUPABASE_URL}/rest/v1/rpc/reclaim_expired_voice_order_requests",
            headers=headers(), json={}, retry_safe=True,
        )

    def pending(self) -> list[dict]:
        self.reclaim_expired()
        return request(
            "GET",
            f"{self.base}/voice_order_requests?status=eq.PENDING&order=created_at.asc&limit=20",
            headers=headers(), retry_safe=True,
        ).json()

    def claim(self, request_id: int) -> str | None:
        # Claiming creates a fresh lease token, so this POST is not safe to retry.
        # If the response is lost after the RPC commits, the lease will expire and
        # the queue reclaimer will make the job available again.
        response = request(
            "POST", f"{SUPABASE_URL}/rest/v1/rpc/claim_voice_order_request",
            headers=headers(), json={"p_id": request_id, "p_worker_id": WORKER_ID},
        )
        token = response.json()
        return token.strip() if isinstance(token, str) and token.strip() else None

    def _completion_already_recorded(self, request_id: int, status: str, result: dict) -> bool:
        rows = request(
            "GET",
            f"{self.base}/voice_order_requests?id=eq.{request_id}&worker_id=eq.{WORKER_ID}&status=eq.{status}&select=id,status,result&limit=1",
            headers=headers(), retry_safe=True,
        ).json()
        return bool(rows and rows[0].get("result") == result)

    def complete(self, request_id: int, status: str, result: dict, lease_token: str) -> None:
        # A stale process cannot finish a job after a later claim replaced its token.
        # PATCH is not blindly retried: verify the state after a lost response.
        try:
            response = request(
                "PATCH",
                f"{self.base}/voice_order_requests?id=eq.{request_id}&worker_id=eq.{WORKER_ID}&lease_token=eq.{lease_token}&status=eq.CLAIMED",
                headers={**headers(), "Prefer": "return=representation"},
                json={"status": status, "completed_at": datetime.now(timezone.utc).isoformat(), "result": result, "lease_until": None, "lease_token": None},
            )
        except RuntimeError:
            if self._completion_already_recorded(request_id, status, result):
                return
            raise
        rows = response.json()
        if isinstance(rows, list) and rows:
            return
        if not self._completion_already_recorded(request_id, status, result):
            raise RuntimeError("request lease was lost before completion")

    def heartbeat(self) -> None:
        global LAST_HEARTBEAT
        request(
            "POST",
            f"{self.base}/voice_worker_heartbeats?on_conflict=worker_id",
            headers={**headers(), "Prefer": "resolution=merge-duplicates"},
            json={"worker_id": WORKER_ID, "status": "IDLE", "details": {"version": "4.7.5", "mode": "pytgcalls-stereo", "engine": "py-tgcalls-2.1.0", "roster": "current-at-execution", "wheel": "multi-winner-elimination"}, "last_seen_at": datetime.now(timezone.utc).isoformat()},
            retry_safe=True,
        )
        LAST_HEARTBEAT = time.monotonic()

    def group_chat_id(self, group_id: int) -> int:
        rows = request("GET", f"{self.base}/groups?id=eq.{group_id}&select=telegram_chat_id&limit=1", headers=headers()).json()
        if not rows or rows[0].get("telegram_chat_id") is None:
            raise RuntimeError(f"group {group_id} has no telegram_chat_id")
        return int(rows[0]["telegram_chat_id"])

    def snapshot(self, group_id: int, people: list[dict]) -> None:
        rows = [{"group_id": group_id, "user_id": int(p["id"]), "display_name": p["display_name"]} for p in people]
        if rows:
            request("POST", f"{self.base}/voice_call_presence_snapshots", headers={**headers(), "Prefer": "return=minimal"}, json=rows)


def claim_safely(store: Store, request_id: int) -> str | None:
    """Skip an ambiguously claimed job without terminating the persistent worker."""
    try:
        return store.claim(request_id)
    except Exception as exc:
        LOG.warning(
            "voice request %s claim failed; queue lease recovery will retry it (%s)",
            request_id,
            type(exc).__name__,
        )
        return None


class VoiceClient:
    def __init__(self) -> None:
        self.client = None
        self.calls = None
        self.active_chats: set[int] = set()
        if Client and raw and TG_API_ID and TG_API_HASH and TG_SESSION_STRING:
            self.client = Client(WORKER_ID, api_id=int(TG_API_ID), api_hash=TG_API_HASH, session_string=TG_SESSION_STRING)
            if PyTgCalls:
                self.calls = PyTgCalls(self.client)

    async def start(self) -> None:
        if not self.client or not self.calls:
            raise RuntimeError("MTProto credentials and py-tgcalls are required")
        await self.client.start()
        await self.calls.start()

    async def close(self) -> None:
        if self.calls:
            for chat_id in list(self.active_chats):
                try:
                    await self.calls.leave_call(chat_id)
                except Exception:
                    pass
        if self.client:
            try:
                await self.client.stop()
            except Exception:
                pass

    async def play(self, chat_id: int, source: str) -> None:
        if not self.calls or not MediaStream or not AudioQuality:
            raise RuntimeError("PyTgCalls stereo engine is not available")
        resolved_source = resolve_safe_source(source)
        stream = MediaStream(
            resolved_source,
            audio_parameters=AudioQuality.STUDIO,
            video_flags=MediaStream.Flags.IGNORE,
        )
        await self.calls.play(chat_id, stream)
        self.active_chats.add(chat_id)

    async def pause(self, chat_id: int) -> None:
        if not self.calls:
            raise RuntimeError("PyTgCalls stereo engine is not available")
        await self.calls.pause(chat_id)

    async def resume(self, chat_id: int) -> None:
        if not self.calls:
            raise RuntimeError("PyTgCalls stereo engine is not available")
        await self.calls.resume(chat_id)

    async def stop(self, chat_id: int) -> None:
        if not self.calls:
            raise RuntimeError("PyTgCalls stereo engine is not available")
        await self.calls.leave_call(chat_id)
        self.active_chats.discard(chat_id)

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
        if self.path not in {"/health", "/heartbeat", "/live"}:
            self.send_response(404); self.end_headers(); return
        if self.path == "/live":
            status = 200
            payload = {"ok": True, "state": "alive"}
        else:
            ready = READY and LAST_HEARTBEAT > 0 and (time.monotonic() - LAST_HEARTBEAT) <= max(HEARTBEAT_SECONDS * 3, 30)
            status = 200 if ready else 503
            payload = {
                "ok": ready,
                "ready": ready,
                "mode": "pytgcalls-stereo",
                "engine": "py-tgcalls-2.1.0",
                "channels": 2,
                "roster": "current-at-execution",
                "wheel": "multi-winner",
                "last_heartbeat_age_seconds": round(time.monotonic() - LAST_HEARTBEAT, 1) if LAST_HEARTBEAT else None,
            }
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
    global READY
    validate_environment()
    store = Store()
    voice = VoiceClient()
    stop = asyncio.Event(); loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    try:
        await voice.start()
        store.heartbeat()
        READY = True
        while not stop.is_set():
            store.heartbeat()
            for command in store.pending():
                request_id = int(command["id"])
                lease_token = claim_safely(store, request_id)
                if not lease_token:
                    continue
                group_id = int(command["group_id"])
                requested = max(1, min(MAX_ROSTER, int(command.get("count") or 1)))
                try:
                    chat_id = store.group_chat_id(group_id)
                    action = str(command.get("action") or "WHEEL").upper()
                    if action in {"PLAY", "PAUSE", "RESUME", "STOP"}:
                        source = str(command.get("source_url") or "").strip()
                        if action == "PLAY":
                            await voice.play(chat_id, source)
                        elif action == "PAUSE":
                            await voice.pause(chat_id)
                        elif action == "RESUME":
                            await voice.resume(chat_id)
                        else:
                            await voice.stop(chat_id)
                        store.complete(request_id, "DONE", {"mode": "PYTG_CALLS_STEREO", "action": action, "chat_id": chat_id}, lease_token)
                        continue
                    if action != "WHEEL":
                        raise RuntimeError("unsupported voice action")
                    people = await voice.participants(chat_id)
                    if not people:
                        raise RuntimeError("در این لحظه فردی در ویس‌کال حاضر نیست.")
                    chosen_count = min(requested, len(people))
                    store.snapshot(group_id, people)
                    await notify(chat_id, people, chosen_count)
                    result_users = [{"id": p["id"], "username": p["username"], "name": p["display_name"]} for p in people]
                    store.complete(request_id, "DONE", {"mode": "CURRENT_ROSTER", "requested_count": requested, "effective_count": chosen_count, "count": len(people), "users": result_users, "wheel": "multi-winner-elimination"}, lease_token)
                except Exception as exc:
                    LOG.exception("voice request %s failed", request_id)
                    store.complete(request_id, "FAILED", {"error": str(exc)[:500]}, lease_token)
            try:
                await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                pass
    finally:
        READY = False
        await voice.close()


if __name__ == "__main__":
    server = serve()
    try:
        asyncio.run(main())
    except Exception:
        LOG.exception("voice worker stopped")
        raise
    finally:
        READY = False
        server.shutdown()
        server.server_close()
