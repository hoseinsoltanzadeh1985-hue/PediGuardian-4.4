#!/usr/bin/env python3
"""Check that every Bot API method used by the webhook still exists in official docs."""
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
WEBHOOK = ROOT / "cloud/supabase/functions/telegram-webhook-v4/index.ts"
DOCS_URL = "https://core.telegram.org/bots/api"


class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        values = dict(attrs)
        href = values.get("href", "")
        if href.startswith("#"):
            self.anchors.add(href[1:].lower())


def used_methods(source: str) -> set[str]:
    return set(re.findall(r'\btg\(\s*["\']([A-Za-z][A-Za-z0-9]+)["\']', source))


def main() -> int:
    request = Request(DOCS_URL, headers={"User-Agent": "PediGuardian-Telegram-Compatibility/1.0"})
    try:
        with urlopen(request, timeout=25) as response:
            if response.status != 200:
                raise RuntimeError(f"Telegram docs returned HTTP {response.status}")
            html = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"ERROR: unable to retrieve official Telegram Bot API docs: {exc}", file=sys.stderr)
        return 2

    parser = AnchorParser()
    parser.feed(html)
    methods = used_methods(WEBHOOK.read_text(encoding="utf-8"))
    missing = sorted(method for method in methods if method.lower() not in parser.anchors)

    print(f"Found {len(methods)} Telegram Bot API methods in webhook source.")
    for method in sorted(methods):
        print(f"{'MISSING' if method in missing else 'OK'}: {method}")
    if missing:
        print("Telegram Bot API compatibility check failed; review the official changelog before changing code.", file=sys.stderr)
        return 1
    print("Telegram Bot API compatibility check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
