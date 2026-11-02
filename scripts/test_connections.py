"""Test the configured model endpoints from the terminal.

Usage:
    .venv/bin/python scripts/test_connections.py

Reads the settings from the app database (same values as the Model settings
page) and pings each configured endpoint with a short timeout, printing the
URL, latency, and precise error messages — much easier to debug than the
in-app Test buttons.

Honors LANGREAD_DATA_DIR like the app itself.
"""

from __future__ import annotations

import sys
import time
from dataclasses import replace

from langread.app_config import db_path
from langread.db import connect
from langread.db.repositories import SettingsRepo
from langread.services.model_settings import ModelSettings, ModelSettingsError

TEST_TIMEOUT = 15.0

_HINTS = (
    "Hints: is the server running on that machine? Is the URL reachable from "
    "this computer (ping/telnet)? For LM Studio and most OpenAI-compatible "
    "servers the base URL must end with /v1 (e.g. http://192.168.1.20:1234/v1). "
    "LM Studio must have 'Serve on local network' enabled."
)


def main() -> int:
    conn = connect(db_path())
    try:
        settings = ModelSettings(SettingsRepo(conn))
        failures = 0
        for prefix, label in (("gen", "Sentence generation model"),
                              ("trans", "Translation model"),
                              ("tts", "Text-to-speech model")):
            print(f"\n=== {label} ({prefix}) ===")
            try:
                if prefix == "tts":
                    config = settings.tts_config()
                else:
                    config = settings.llm_config(prefix)
            except ModelSettingsError as exc:
                print(f"❌ Not configured: {exc}")
                failures += 1
                continue

            print(f"URL:   {config.base_url}")
            print(f"Model: {config.model}")
            config = replace(config, timeout=TEST_TIMEOUT)
            start = time.monotonic()
            try:
                if prefix == "tts":
                    from langread.services.tts import TtsService

                    data = TtsService(config).synthesize("你好")
                    elapsed = time.monotonic() - start
                    print(f"✅ OK — received {len(data)} bytes of MP3 audio "
                          f"in {elapsed:.1f}s")
                else:
                    from langread.services.llm_client import LlmClient

                    reply = LlmClient(config).chat(
                        "Reply with exactly: OK", temperature=0.0
                    )
                    elapsed = time.monotonic() - start
                    print(f"✅ OK — model replied {reply!r} in {elapsed:.1f}s")
            except Exception as exc:  # noqa: BLE001 - diagnostics tool
                elapsed = time.monotonic() - start
                print(f"❌ FAILED after {elapsed:.1f}s: "
                      f"{type(exc).__name__}: {exc}")
                print(_HINTS)
                failures += 1
        print()
        if failures:
            print(f"{failures} endpoint(s) failed.")
            return 1
        print("All configured endpoints responded.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
