"""Text-to-speech client for OpenAI-compatible endpoints (Kokoro, §9.3).

Accepts any common audio format the endpoint returns (MP3, WAV, OGG, FLAC).
Chinese voices skip Latin text, so mixed-script text is split into runs:
Chinese runs use the main (Chinese) voice, Latin runs (letters/digits) use
`latin_voice` (an English voice), and the audio is spliced back together.
`speed` is only sent when it differs from 1.0 (not every server accepts it).
"""

from __future__ import annotations

import re
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
    latin_voice: str | None = None  # English voice for Latin runs
    speed: float = 1.0
    timeout: float = 600.0


class TtsError(Exception):
    """Any failure synthesizing or validating audio."""


_CJK_CHAR_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"  # ideographs
    r"\u3000-\u303f\uff00-\uffef"                 # CJK punctuation / fullwidth
    r"\u2018\u2019\u201c\u201d\u2013\u2014\u2026]"  # curly quotes, dashes, ellipsis
)


def _classify_char(ch: str) -> str | None:
    if _CJK_CHAR_RE.match(ch):
        return "zh"
    if ch.isascii() and ch.isalnum():
        return "latin"
    return None  # spaces and neutral punctuation attach to a neighbor


def split_by_script(text: str) -> list[tuple[str, str]]:
    """Split text into [(segment, 'zh'|'latin')] runs, keeping order.

    Neutral characters (spaces, ASCII punctuation) attach to the following
    run, or to the previous run at the end of the text.
    """
    parts: list[tuple[str, str]] = []
    buf = ""
    cur_type: str | None = None
    pending = ""
    for ch in text:
        char_type = _classify_char(ch)
        if char_type is None:
            pending += ch
            continue
        if cur_type is None:
            cur_type, buf, pending = char_type, pending + ch, ""
        elif char_type == cur_type:
            buf += pending + ch
            pending = ""
        else:
            parts.append((buf, cur_type))
            cur_type, buf, pending = char_type, pending + ch, ""
    if cur_type is not None:
        parts.append((buf + pending, cur_type))
    return [part for part in parts if part[0].strip()]


# characters a TTS engine can actually voice
_SPEAKABLE_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaffA-Za-z0-9]")


def _is_speakable(ch: str) -> bool:
    return bool(_SPEAKABLE_RE.match(ch))


def merge_unspeakable(segments: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Merge punctuation-only segments into a neighbor and combine adjacent
    same-kind segments.

    Some TTS servers reject input that contains no speakable characters
    (e.g. a lone '。' between two Latin runs) with a 500 error.
    """
    result: list[list[str]] = []  # mutable [text, kind]
    pending = ""
    for text, kind in segments:
        if not any(_is_speakable(ch) for ch in text):
            pending += text  # nothing speakable → attach to a neighbor
            continue
        if pending:
            if result:
                result[-1][0] += pending  # attach to the previous segment
            else:
                text = pending + text     # leading punctuation → next segment
            pending = ""
        if result and result[-1][1] == kind:
            result[-1][0] += text         # combine adjacent same-kind runs
        else:
            result.append([text, kind])
    if pending and result:
        result[-1][0] += pending
    return [(text, kind) for text, kind in result]


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


# CJK punctuation transliterated for Latin (English-voice) segments —
# English voices ignore CJK punctuation, so periods would vanish silently.
_CJK_TO_ASCII_PUNCT = {
    "。": ". ", "！": "! ", "？": "? ", "，": ", ", "、": ", ",
    "：": ": ", "；": "; ", "（": " (", "）": ") ",
    "“": '"', "”": '"', "‘": "'", "’": "'",
}


def _latinize_punctuation(text: str) -> str:
    return "".join(_CJK_TO_ASCII_PUNCT.get(ch, ch) for ch in text)


def _strip_id3(data: bytes) -> bytes:
    """Remove a leading ID3v2 tag and trailing ID3v1 tag (raw frames remain).

    Concatenating whole MP3 files leaves ID3 tags mid-stream, which makes
    decoders log 'Header missing' warnings at every join.
    """
    if data[:3] == b"ID3" and len(data) >= 10:
        size = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | (
            (data[8] & 0x7F) << 7
        ) | (data[9] & 0x7F)
        footer = 10 if (data[5] & 0x10) else 0
        data = data[10 + size + footer:]
    if len(data) > 128 and data[-128:-125] == b"TAG":
        data = data[:-128]
    return data


# ---- minimal MPEG audio frame parsing (Layer III) ----

_BITRATES_L3_V1 = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
_BITRATES_L3_V2 = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160)
_SAMPLERATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000),
                0: (11025, 12000, 8000)}


def _parse_mp3_frame(data: bytes, pos: int = 0) -> tuple[int, int] | None:
    """Parse an MPEG-1/2/2.5 Layer III frame header at `pos`.

    Returns (frame_size, side_info_size) or None if not a valid header.
    """
    if pos + 4 > len(data):
        return None
    b1, b2, b3 = data[pos + 1], data[pos + 2], data[pos + 3]
    if data[pos] != 0xFF or (b1 & 0xE0) != 0xE0:
        return None
    version = (b1 >> 3) & 3
    layer = (b1 >> 1) & 3
    if version not in (3, 2, 0) or layer != 1:
        return None
    bitrate_idx = (b2 >> 4) & 0xF
    samplerate_idx = (b2 >> 2) & 3
    padding = (b2 >> 1) & 1
    if bitrate_idx in (0, 15) or samplerate_idx == 3:
        return None
    bitrate = (_BITRATES_L3_V1 if version == 3 else _BITRATES_L3_V2)[bitrate_idx] * 1000
    samplerate = _SAMPLERATES[version][samplerate_idx]
    divisor = 144 if version == 3 else 72
    frame_size = divisor * bitrate // samplerate + padding
    if frame_size <= 4:
        return None
    mono = ((b3 >> 6) & 3) == 3
    side_info = (17 if mono else 32) if version == 3 else (9 if mono else 17)
    return frame_size, side_info


def _strip_leading_xing(data: bytes) -> bytes:
    """Remove a leading Xing/Info frame (encoders write one per file with
    that file's frame count — left mid-stream it makes decoders report an
    'invalid concatenated file')."""
    parsed = _parse_mp3_frame(data)
    if parsed is None:
        return data
    frame_size, side_info = parsed
    if len(data) < frame_size:
        return data
    if data[4 + side_info:4 + side_info + 4] in (b"Xing", b"Info"):
        return data[frame_size:]
    return data


def _count_mp3_frames(data: bytes) -> int | None:
    """Walk the frame stream; None if it is not a clean frame sequence."""
    count = 0
    pos = 0
    while pos < len(data):
        parsed = _parse_mp3_frame(data, pos)
        if parsed is None:
            return None
        frame_size = parsed[0]
        if pos + frame_size > len(data):
            break  # trailing partial frame — ignore
        count += 1
        pos += frame_size
    return count or None


def _make_xing_frame(template_header: bytes, frame_count: int,
                      byte_count: int) -> bytes | None:
    """Build a Xing header frame (declares total frames/bytes) so decoders
    get an exact duration instead of estimating and warning."""
    parsed = _parse_mp3_frame(template_header)
    if parsed is None:
        return None
    frame_size, side_info = parsed
    body = (b"Xing" + struct.pack(">I", 0x0003)          # frames + bytes
            + struct.pack(">I", frame_count) + struct.pack(">I", byte_count))
    frame = template_header[:4] + b"\x00" * side_info + body
    if len(frame) > frame_size:
        return None  # frame too small for the tag — skip the header
    return frame + b"\x00" * (frame_size - len(frame))


def concat_audio(chunks: list[bytes], audio_format: str) -> bytes:
    """Concatenate same-format audio chunks into one file's bytes.

    MP3: ID3 tags and per-chunk Xing/Info frames are stripped, and a single
    correct Xing header is prepended (exact duration, no decoder warnings).
    WAV: merged under one RIFF header with a corrected data size.
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
    if audio_format == "mp3":
        stream = b"".join(
            _strip_leading_xing(_strip_id3(chunk)) for chunk in chunks
        )
        frame_count = _count_mp3_frames(stream)
        if frame_count:
            xing = _make_xing_frame(
                stream[:4], frame_count,
                byte_count=len(stream) + _parse_mp3_frame(stream)[0],
            )
            if xing is not None:
                return xing + stream
        return stream
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
        """Synthesize `text` and return validated audio bytes (any format).

        Mixed-script text (Chinese + Latin) is synthesized run by run —
        Chinese runs with the main voice, Latin runs with `latin_voice` —
        and spliced back together in order.
        """
        segments = merge_unspeakable(split_by_script(text))
        has_latin = any(kind == "latin" for _seg, kind in segments)
        latin_voice = (self._config.latin_voice or "").strip()
        if not has_latin or not latin_voice:
            # single call with the whole text (pure Chinese or no latin voice)
            speakable = any(_is_speakable(ch) for ch in text)
            if not speakable:
                raise TtsError(
                    "text contains no speakable characters "
                    f"(mp3/wav voices need letters): {text!r}"
                )
            return self._synthesize_segment(text, self._config.voice)

        chunks: list[bytes] = []
        for segment, kind in segments:
            voice = latin_voice if kind == "latin" else self._config.voice
            if kind == "latin":
                # English voices ignore CJK punctuation — transliterate so
                # sentence periods still produce audible pauses
                segment = _latinize_punctuation(segment)
            chunks.append(self._synthesize_segment(segment, voice))
        audio_format = detect_audio_format(chunks[0])
        return concat_audio(chunks, audio_format)

    def _synthesize_segment(self, text: str, voice: str | None) -> bytes:
        """One request with one voice; validates the returned audio."""
        kwargs: dict = {
            "model": self._config.model,
            "input": text,
            "voice": voice or "default",
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
