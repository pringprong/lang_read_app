"""Text-to-speech client for OpenAI-compatible endpoints (Kokoro, §9.3).

Produces MP3 bytes via the `/audio/speech` endpoint. `speed` is only sent
when it differs from 1.0 (not every compatible server accepts it).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI


@dataclass(frozen=True)
class TtsConfig:
    base_url: str
    model: str
    api_key: str | None = None
    voice: str | None = None
    speed: float = 1.0
    timeout: float = 600.0


class TtsError(Exception):
    """Any failure synthesizing or validating audio."""


def looks_like_mp3(data: bytes) -> bool:
    """True if the bytes start with an ID3 tag or an MPEG frame sync word."""
    if data.startswith(b"ID3"):
        return True
    return len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0


class TtsService:
    def __init__(self, config: TtsConfig) -> None:
        self._config = config
        self._client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key or "not-set",
            timeout=config.timeout,
            max_retries=1,
        )

    def synthesize(self, text: str) -> bytes:
        """Synthesize `text` and return validated MP3 bytes."""
        kwargs: dict = {
            "model": self._config.model,
            "input": text,
            "voice": self._config.voice or "default",
            "response_format": "mp3",
        }
        if self._config.speed != 1.0:
            kwargs["speed"] = self._config.speed
        try:
            response = self._client.audio.speech.create(**kwargs)
        except Exception as exc:
            raise TtsError(f"TTS request failed: {exc}") from exc
        data = getattr(response, "content", None)
        if not data:
            raise TtsError("TTS endpoint returned no audio content")
        if not looks_like_mp3(bytes(data)):
            head = bytes(data[:32])
            raise TtsError(f"TTS response is not MP3 data (starts with {head!r})")
        return bytes(data)

    def synthesize_to_file(self, text: str, out_path: Path) -> Path:
        """Synthesize `text` and write it to `out_path` (lesson MP3, D-1)."""
        data = self.synthesize(text)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        return out_path

    def synthesize_texts_to_file(self, texts: list[str], out_path: Path) -> Path:
        """Synthesize each text (one call per paragraph, avoiding request-size
        limits) and concatenate the MP3 frames into a single file (D-1)."""
        chunks = [self.synthesize(text) for text in texts]
        data = b"".join(chunks)
        if not looks_like_mp3(data):
            raise TtsError("concatenated audio is not valid MP3 data")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        return out_path
