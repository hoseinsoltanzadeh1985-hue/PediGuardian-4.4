import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const SECRET = Deno.env.get("TELEGRAM_WEBHOOK_SECRET") ?? "";
const TARGET = `${Deno.env.get("SUPABASE_URL") ?? "https://ygzabgsyfehmlaarphpx.supabase.co"}/functions/v1/telegram-webhook-v4`;

function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json;charset=utf-8", "cache-control": "no-store" }
  });
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("OK", { status: 200 });
  if (!SECRET) return json({ ok: false, error: "not_configured" }, 500);
  if (req.headers.get("x-telegram-bot-api-secret-token") !== SECRET) return new Response("Unauthorized", { status: 401 });
  try {
    const body = await req.text();
    const upstream = await fetch(TARGET, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-telegram-bot-api-secret-token": SECRET
      },
      body
    });
    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") ?? "application/json", "cache-control": "no-store" }
    });
  } catch (error) {
    console.error("webhook proxy error", error);
    return json({ ok: false, error: "upstream_unavailable" }, 502);
  }
});
