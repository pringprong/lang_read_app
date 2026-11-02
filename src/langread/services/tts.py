"""Text-to-speech client for OpenAI-compatible endpoints (Kokoro, §9.3).

Accepts any common audio format the endpoint returns (MP3, WAV, OGG, FLAC)
— servers differ: Kokoro-FastAPI returns MP3, some return WAV. `speed` is
only sent when it differs from 1.0 (not every compatible server accepts it).
"""

from __future__ import annotations

import struct
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


def detect_audio_format(data: bytes) -> str | None:
    """Identify common audio formats by header. Returns 'mp3', 'wav',
    'ogg', or 'flac' — None for anything else."""
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return "wav"
    if data.startswith(b"ID3"):
        return "mp3"
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return "mp3"  # MPEG frame sync word
    if data.startswith(b"OggS"):
        return "ogg"
    if data.startswith(b"fLaC"):
        return "flac"
    return None


def looks_like_mp3(data: bytes) -> bool:
    """True if the bytes start with an ID3 tag or an MPEG frame sync word."""
    return detect_audio_format(data) == "mp3"


def _parse_wav(data: bytes) -> tuple[bytes, bytes]:
    """Split a canonical RIFF/WAVE file into (fmt chunk bytes, data bytes)."""
    if not data.startswith(b"RIFF"):
        raise TtsError("not a RIFF/WAVE file")
    fmt = b""
    payload = b""
    pos = 12
    while pos + 8 <= len(data):
        chunk_id = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + size]
        if chunk_id == b"fmt ":
            fmt = data[pos:pos + 8] + body
        elif chunk_id == b"data":
            payload += body
        pos += 8 + size + (size & 1)  # chunks are word-aligned
    if not fmt or not payload:
        raise TtsError("WAVE file missing fmt/data chunks")
    return fmt, payload


def concat_audio(chunks: list[bytes], audio_format: str) -> bytes:
    """Concatenate same-format audio chunks into one file's bytes.

    MP3/OGG frames concatenate natively; WAV files must be merged under a
    single RIFF header with a corrected data size.
    """
    if audio_format == "wav":
        fmt, total_data = b"", b""
        for chunk in chunks:
            chunk_fmt, chunk_data = _parse_wav(chunk)
            fmt = fmt or chunk_fmt
            total_data += chunk_data
        riff_size = 4 + len(fmt) + 8 + len(total_data)
        return (
            b"RIFF" + struct.pack("<I", riff_size) + b"WAVE"
            + fmt + b"data" + struct.pack("<I", len(total_data)) + total_data
        )
    return b"".join(chunks)


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
        """Synthesize `text` and return validated audio bytes (any format)."""
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
        data = bytes(data)
        # some servers reply with JSON errors and HTTP 200 — catch that too
        audio_format = detect_audio_format(data)
        if audio_format is None:
            head = data[:64]
            if head.lstrip().startswith(b"{") or b"error" in head.lower():
                raise TtsError(f"TTS endpoint returned an error: {head!r}")
            raise TtsError(
                f"TTS response is not recognized audio "
                f"(mp3/wav/ogg/flac); starts with {head[:16]!r}"
            )
        return data

    def synthesize_to_file(self, text: str, out_path: Path) -> Path:
        """Synthesize `text` and write it to `out_path` (lesson audio, D-1)."""
        data = self.synthesize(text)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        return out_path

    def synthesize_texts_to_file(self, texts: list[str], out_path: Path) -> Path:
        """Synthesize each text (one call per paragraph, avoiding request-size
        limits) and concatenate the audio into a single file (D-1)."""
        chunks = [self.synthesize(text) for text in texts]
        audio_format = detect_audio_format(chunks[0])
        data = concat_audio(chunks, audio_format)
        if detect_audio_format(data) is None:
            raise TtsError("concatenated audio is not valid")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        return out_path
