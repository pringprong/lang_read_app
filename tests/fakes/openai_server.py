"""A local fake OpenAI-compatible server for integration tests.

Implements:
  POST /v1/chat/completions  → canned reply (optionally broken JSON first)
  POST /v1/audio/speech      → fake MP3 or WAV bytes (optionally garbage)
"""

from __future__ import annotations

import json
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def make_wav(num_samples: int = 100) -> bytes:
    """A minimal valid PCM 16-bit mono 24 kHz WAV file."""
    fmt = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, 24000, 48000, 2, 16)
    payload = b"\x00\x01" * num_samples
    data = b"data" + struct.pack("<I", len(payload)) + payload
    riff = b"RIFF" + struct.pack("<I", 4 + len(fmt) + len(data)) + b"WAVE"
    return riff + fmt + data


def make_mp3() -> bytes:
    """A minimal 'MP3': ID3v2 header (size 0) + an MPEG frame sync + zeros."""
    return b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\xff\xfb" + b"\x00" * 62


class FakeOpenAiServer:
    def __init__(self) -> None:
        self.chat_calls: list[dict] = []
        self.speech_calls: list[dict] = []
        self.break_json_once = False  # first chat call returns non-JSON
        self.break_mp3 = False        # speech returns non-audio bytes
        self.return_wav = False       # speech returns WAV instead of MP3
        self.empty_content_once = False  # first chat call returns empty content
        self._lock = threading.Lock()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # ---- lifecycle ----

    def start(self) -> str:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:  # silence
                pass

            def _read_body(self) -> dict:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    return json.loads(raw or b"{}")
                except json.JSONDecodeError:
                    return {}

            def _send(self, status: int, payload, content_type: str) -> None:
                body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:  # noqa: N802 (http.server naming)
                body = self._read_body()
                if self.path.endswith("/chat/completions"):
                    with outer._lock:
                        outer.chat_calls.append(body)
                        broken = outer.break_json_once
                        if broken:
                            outer.break_json_once = False
                        empty = outer.empty_content_once
                        if empty:
                            outer.empty_content_once = False
                    prompt = ""
                    for message in body.get("messages", []):
                        if message.get("role") == "user":
                            prompt = message.get("content", "")
                    if empty:
                        content = ""  # simulate a reasoning model's empty reply
                    elif broken:
                        content = "Sure! Here you go: (not valid json"
                    elif "JSON" in prompt or "json" in prompt:
                        content = '["你好", "世界"]'
                    else:
                        content = "OK"
                    self._send(
                        200,
                        {"choices": [{"message": {"role": "assistant",
                                                  "content": content}}]},
                        "application/json",
                    )
                elif self.path.endswith("/audio/speech"):
                    with outer._lock:
                        outer.speech_calls.append(body)
                        bad = outer.break_mp3
                        wav = outer.return_wav
                    if bad:
                        data = b"<html>error</html>"
                    elif wav:
                        data = make_wav()
                    else:
                        data = make_mp3()
                    self._send(200, data, "audio/mpeg")
                else:
                    self._send(404, {"error": "not found"}, "application/json")

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def base_url(self) -> str:
        return self._url + "/v1"

    _url: str = ""

    def start_and_url(self) -> str:
        self._url = self.start()
        return self.base_url

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server = None

