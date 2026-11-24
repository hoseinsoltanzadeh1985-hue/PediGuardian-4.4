export type FetchLike = (input: string | URL | Request, init?: RequestInit) => Promise<Response>;

export interface TelegramClientOptions {
  token: string;
  fetchImpl?: FetchLike;
}

export interface TelegramEnvelope<T> {
  ok: boolean;
  result?: T;
  description?: string;
  error_code?: number;
}

export function createTelegramClient({ token, fetchImpl = fetch }: TelegramClientOptions) {
  if (!token || !token.trim()) throw new TypeError("Telegram bot token is required");
  const base = `https://api.telegram.org/bot${token.trim()}`;

  return async function call(method: string, payload: Record<string, unknown> = {}): Promise<any> {
    if (!/^[A-Za-z][A-Za-z0-9]{0,63}$/.test(method)) {
      throw new TypeError("Invalid Telegram Bot API method name");
    }
    const response = await fetchImpl(`${base}/${method}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });

    let envelope: TelegramEnvelope<any>;
    try {
      envelope = await response.json() as TelegramEnvelope<any>;
    } catch {
      throw new Error(`Telegram API ${method} returned invalid JSON (HTTP ${response.status})`);
    }

    if (!response.ok || envelope?.ok !== true) {
      const code = envelope?.error_code ?? response.status;
      const description = typeof envelope?.description === "string"
        ? envelope.description.slice(0, 300)
        : "request failed";
      throw new Error(`Telegram API ${method} failed (${code}): ${description}`);
    }
    return envelope.result;
  };
}
