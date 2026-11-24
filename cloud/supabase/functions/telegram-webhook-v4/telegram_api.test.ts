import assert from "node:assert/strict";
import test from "node:test";
import { createTelegramClient, type FetchLike } from "./telegram_api.ts";

function fakeFetch(handler: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const fetchImpl: FetchLike = async (input, init) => {
    const url = String(input);
    calls.push({ url, init });
    return await handler(url, init);
  };
  return { fetchImpl, calls };
}

test("client rejects a missing token before making network requests", () => {
  assert.throws(() => createTelegramClient({ token: "" }), /token is required/);
  assert.throws(() => createTelegramClient({ token: "   " }), /token is required/);
});

test("successful Bot API response returns result and sends JSON POST", async () => {
  const { fetchImpl, calls } = fakeFetch(() => Response.json({ ok: true, result: { id: 42, is_bot: true } }));
  const tg = createTelegramClient({ token: "test-token", fetchImpl });
  const result = await tg<{ id: number; is_bot: boolean }>("getMe", {});
  assert.deepEqual(result, { id: 42, is_bot: true });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "https://api.telegram.org/bottest-token/getMe");
  assert.equal(calls[0].init?.method, "POST");
  assert.equal((calls[0].init?.headers as Record<string, string>)["content-type"], "application/json");
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {});
});

test("payload is preserved for methods with required parameters", async () => {
  const payload = { chat_id: -100123, user_id: 77, only_if_banned: true };
  const { fetchImpl, calls } = fakeFetch(() => Response.json({ ok: true, result: { status: "administrator" } }));
  const tg = createTelegramClient({ token: "t", fetchImpl });
  await tg("getChatMember", payload);
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), payload);
});

test("Telegram API-level errors reject even when HTTP status is 200", async () => {
  const { fetchImpl } = fakeFetch(() => Response.json({
    ok: false, error_code: 400, description: "Bad Request: chat not found",
  }));
  const tg = createTelegramClient({ token: "t", fetchImpl });
  await assert.rejects(() => tg("getChat", { chat_id: 1 }), /failed \(400\).*chat not found/);
});

test("HTTP errors reject and preserve Telegram error details", async () => {
  const { fetchImpl } = fakeFetch(() => Response.json({
    ok: false, error_code: 401, description: "Unauthorized",
  }, { status: 401 }));
  const tg = createTelegramClient({ token: "t", fetchImpl });
  await assert.rejects(() => tg("getMe"), /failed \(401\).*Unauthorized/);
});

test("invalid JSON response fails closed", async () => {
  const { fetchImpl } = fakeFetch(() => new Response("upstream proxy error", { status: 502 }));
  const tg = createTelegramClient({ token: "t", fetchImpl });
  await assert.rejects(() => tg("getMe"), /returned invalid JSON \(HTTP 502\)/);
});

test("method names are validated before any network request", async () => {
  const { fetchImpl, calls } = fakeFetch(() => Response.json({ ok: true, result: true }));
  const tg = createTelegramClient({ token: "t", fetchImpl });
  await assert.rejects(() => tg("../getMe"), /Invalid Telegram Bot API method name/);
  await assert.rejects(() => tg("getMe?x=1"), /Invalid Telegram Bot API method name/);
  assert.equal(calls.length, 0);
});

test("network failures propagate without blind retry of non-idempotent methods", async () => {
  let count = 0;
  const { fetchImpl } = fakeFetch(() => {
    count++;
    throw new Error("connection reset");
  });
  const tg = createTelegramClient({ token: "t", fetchImpl });
  await assert.rejects(() => tg("sendMessage", { chat_id: 1, text: "hello" }), /connection reset/);
  assert.equal(count, 1);
});

test("tokens are not included in thrown API error messages", async () => {
  const secret = "123456:super-secret";
  const { fetchImpl } = fakeFetch(() => Response.json({
    ok: false, error_code: 401, description: "Unauthorized",
  }, { status: 401 }));
  const tg = createTelegramClient({ token: secret, fetchImpl });
  await assert.rejects(
    () => tg("getMe"),
    (error: Error) => !error.message.includes(secret),
  );
});
