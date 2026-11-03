"""M3 integration tests: LLM + TTS clients against the fake server."""

from __future__ import annotations

import pytest

from langread.services.llm_client import LlmClient, LlmConfig, LlmError, extract_json
from langread.services.tts import (
    TtsConfig,
    TtsError,
    TtsService,
    _count_mp3_frames,
    _latinize_punctuation,
    _strip_id3,
    _strip_leading_xing,
    concat_audio,
    detect_audio_format,
    looks_like_mp3,
    merge_unspeakable,
    split_by_script,
)

from tests.fakes.openai_server import FakeOpenAiServer, make_mp3, make_wav


@pytest.fixture()
def server():
    fake = FakeOpenAiServer()
    fake.start_and_url()
    yield fake
    fake.stop()


def test_chat_returns_reply(server):
    client = LlmClient(LlmConfig(base_url=server.base_url, model="fake"))
    assert client.chat("hello") == "OK"
    assert len(server.chat_calls) == 1


def test_chat_json_parses_array(server):
    client = LlmClient(LlmConfig(base_url=server.base_url, model="fake"))
    result = client.chat_json("Return JSON array of words")
    assert result == ["你好", "世界"]


def test_chat_json_retries_after_bad_json(server):
    server.break_json_once = True
    client = LlmClient(LlmConfig(base_url=server.base_url, model="fake"))
    result = client.chat_json("Return JSON array of words")
    assert result == ["你好", "世界"]
    assert len(server.chat_calls) == 2  # one bad reply + one fix-up retry


def test_chat_connection_failure_raises_llm_error():
    client = LlmClient(LlmConfig(base_url="http://127.0.0.1:1/v1", model="x"))
    with pytest.raises(LlmError):
        client.chat("hello")


def test_chat_retries_after_empty_reply(server):
    """Reasoning models occasionally return empty content — chat retries."""
    server.empty_content_once = True
    client = LlmClient(LlmConfig(base_url=server.base_url, model="fake"))
    assert client.chat("hello") == "OK"  # retry succeeded
    assert len(server.chat_calls) == 2


def test_tts_synthesizes_mp3(server, tmp_path):
    service = TtsService(
        TtsConfig(base_url=server.base_url, model="kokoro", voice="zf_xiaobei")
    )
    data = service.synthesize("你好")
    assert looks_like_mp3(data)
    assert len(server.speech_calls) == 1
    assert server.speech_calls[0]["input"] == "你好"

    out = tmp_path / "audio" / "lesson_1.mp3"
    service.synthesize_to_file("你好世界", out)
    assert out.exists() and out.read_bytes() == data


def test_tts_rejects_non_mp3_response(server):
    server.break_mp3 = True
    service = TtsService(TtsConfig(base_url=server.base_url, model="kokoro"))
    with pytest.raises(TtsError):
        service.synthesize("你好")


def test_tts_accepts_wav_response(server):
    """Servers that return WAV (e.g. some OpenAI-compatible TTS) are fine."""
    server.return_wav = True
    service = TtsService(TtsConfig(base_url=server.base_url, model="kokoro"))
    data = service.synthesize("你好")
    assert detect_audio_format(data) == "wav"
    assert looks_like_mp3(data) is False


def test_detect_audio_format():
    assert detect_audio_format(b"ID3" + b"\x00" * 10) == "mp3"
    assert detect_audio_format(b"\xff\xfb" + b"\x00" * 10) == "mp3"
    assert detect_audio_format(make_wav()) == "wav"
    assert detect_audio_format(b"OggS" + b"\x00" * 10) == "ogg"
    assert detect_audio_format(b"fLaC" + b"\x00" * 10) == "flac"
    assert detect_audio_format(b"not audio at all") is None
    assert detect_audio_format(b"") is None


def test_concat_audio_wav_merge():
    chunks = [make_wav(50), make_wav(30)]
    merged = concat_audio(chunks, "wav")
    assert detect_audio_format(merged) == "wav"
    from langread.services.tts import _parse_wav

    _fmt, data = _parse_wav(merged)
    assert len(data) == 80 * 2  # 50 + 30 samples × 2 bytes
    # RIFF size field covers the whole file
    import struct

    assert struct.unpack("<I", merged[4:8])[0] == len(merged) - 8


def test_concat_audio_mp3_join():
    """MP3 chunks are concatenated with ID3 tags stripped — tags left
    mid-stream cause decoder 'Header missing' warnings at every join."""
    chunk = make_mp3()
    merged = concat_audio([chunk, chunk], "mp3")
    assert merged == (b"\xff\xfb" + b"\x00" * 62) * 2
    assert detect_audio_format(merged) == "mp3"


def test_strip_id3():
    tagged = (b"ID3\x04\x00\x00"          # ID3v2.4 header, no flags
              + b"\x00\x00\x00\x02"       # syncsafe tag size = 2
              + b"xx"                     # 2 bytes of tag body
              + b"\xff\xfb" + b"f" * 10   # MPEG frames
              + b"TAG" + b"t" * 125)      # ID3v1 trailer
    assert _strip_id3(tagged) == b"\xff\xfb" + b"f" * 10
    # data without tags passes through unchanged
    assert _strip_id3(b"\xff\xfbdata") == b"\xff\xfbdata"


def test_latinize_punctuation():
    """English voices ignore CJK punctuation — transliterate for Latin runs."""
    assert _latinize_punctuation("HSK。HSK，") == "HSK. HSK, "
    assert _latinize_punctuation("HSK") == "HSK"


# ---- MP3 frame handling (Kokoro-style chunks) ----

_KOKORO_HEADER = b"\xff\xf3\x84\xc0"  # MPEG-2 L3, 64 kbps, 24 kHz, mono
_KOKORO_FRAME_SIZE = 192               # 72 * 64000 / 24000


def _kokoro_frame(marker: bytes = b"") -> bytes:
    body = bytearray(b"\x00" * (_KOKORO_FRAME_SIZE - 4))
    if marker:
        body[9:9 + len(marker)] = marker  # after 9-byte MPEG-2 mono side info
    return _KOKORO_HEADER + bytes(body)


def _kokoro_chunk(audio_frames: int) -> bytes:
    """ID3 tag + Info frame + N audio frames — like a real Kokoro response."""
    info = _kokoro_frame(b"Info")
    audio = _kokoro_frame() * audio_frames
    return b"ID3\x04\x00\x00\x00\x00\x00\x00" + info + audio


def test_concat_audio_builds_single_xing_header():
    """Concatenated MP3s get ONE Xing header with the true totals; the
    per-chunk Info frames (which make decoders report an 'invalid
    concatenated file') are removed."""
    chunks = [_kokoro_chunk(3), _kokoro_chunk(2)]
    merged = concat_audio(chunks, "mp3")
    assert detect_audio_format(merged) == "mp3"
    # single Xing frame first
    assert merged[:4] == _KOKORO_HEADER
    assert merged[13:17] == b"Xing"
    assert int.from_bytes(merged[21:25], "big") == 5  # 3 + 2 audio frames
    assert int.from_bytes(merged[25:29], "big") == len(merged)  # exact size
    # no leftover Info/Xing markers mid-stream
    assert merged.count(b"Info") == 0
    assert merged.count(b"Xing") == 1


def test_strip_leading_xing_and_count_frames():
    chunk = _kokoro_chunk(2)
    stripped = _strip_leading_xing(_strip_id3(chunk))
    assert stripped == _kokoro_frame() * 2
    assert _count_mp3_frames(stripped) == 2
    assert _count_mp3_frames(_kokoro_frame() * 7) == 7
    # garbage (the fake-server mp3) is not countable → callers fall back
    assert _count_mp3_frames(make_mp3()[10:]) is None


def test_tts_json_error_response_reported(server):
    """Non-audio replies (some servers return errors with HTTP 200) are
    reported with the response head, not accepted as audio."""
    server.break_mp3 = True
    service = TtsService(TtsConfig(base_url=server.base_url, model="kokoro"))
    with pytest.raises(TtsError, match="not recognized audio|error"):
        service.synthesize("你好")


# ---- mixed-script synthesis (Chinese voice skips Latin text) ----


def test_split_by_script():
    # pure Chinese (with punctuation) → one run
    assert split_by_script("今天天气很好。") == [("今天天气很好。", "zh")]
    # pure Latin → one run
    assert split_by_script("HSK exam") == [("HSK exam", "latin")]
    # mixed: order preserved, punctuation attached sensibly
    parts = split_by_script("我要考HSK考试。")
    assert [kind for _s, kind in parts] == ["zh", "latin", "zh"]
    assert parts[1][0] == "HSK"
    assert "".join(seg for seg, _k in parts) == "我要考HSK考试。"
    # spaces between scripts
    parts = split_by_script("HSK 很好")
    assert [kind for _s, kind in parts] == ["latin", "zh"]


def test_tts_mixed_text_uses_both_voices(server):
    """Chinese runs use the main voice; Latin runs use the latin voice."""
    service = TtsService(
        TtsConfig(base_url=server.base_url, model="kokoro",
                  voice="zf_xiaobei", latin_voice="af_heart")
    )
    data = service.synthesize("我要考HSK考试。")
    assert looks_like_mp3(data)
    assert len(server.speech_calls) == 3  # zh + latin + zh
    voices = [call["voice"] for call in server.speech_calls]
    assert voices == ["zf_xiaobei", "af_heart", "zf_xiaobei"]
    inputs = [call["input"] for call in server.speech_calls]
    assert inputs[0] == "我要考"
    assert inputs[1] == "HSK"


def test_tts_pure_chinese_single_call_even_with_latin_voice(server):
    service = TtsService(
        TtsConfig(base_url=server.base_url, model="kokoro",
                  voice="zf_xiaobei", latin_voice="af_heart")
    )
    service.synthesize("你好。")
    assert len(server.speech_calls) == 1


def test_tts_mixed_text_without_latin_voice_skips(server):
    """No latin voice configured → old behavior: one call, Latin skipped."""
    service = TtsService(
        TtsConfig(base_url=server.base_url, model="kokoro", voice="zf_xiaobei")
    )
    service.synthesize("我要考HSK考试。")
    assert len(server.speech_calls) == 1
    assert server.speech_calls[0]["voice"] == "zf_xiaobei"


def test_merge_unspeakable():
    """A lone '。' between two Latin runs merges into a neighbor — some TTS
    servers 500 on punctuation-only input."""
    segments = split_by_script("我在学习HSK。HSK的内容很丰富。")
    assert ("。", "zh") in segments  # the problem segment exists pre-merge
    merged = merge_unspeakable(segments)
    # no punctuation-only segments remain
    for text, _kind in merged:
        assert any(ch.isalnum() or "\u4e00" <= ch <= "\u9fff" for ch in text)
    # adjacent same-kind runs are combined
    kinds = [kind for _t, kind in merged]
    assert kinds == ["zh", "latin", "zh"]
    assert merged[1][0] == "HSK。HSK"
    # leading punctuation attaches forward
    assert merge_unspeakable([("。", "zh"), ("你好", "zh")]) == [("。你好", "zh")]


def test_tts_mixed_text_never_sends_punctuation_only(server):
    """Regression: the 500 from a punctuation-only request (lone '。')."""
    service = TtsService(
        TtsConfig(base_url=server.base_url, model="kokoro",
                  voice="zf_xiaobei", latin_voice="af_heart")
    )
    service.synthesize("我在学习HSK。")
    inputs = [call["input"] for call in server.speech_calls]
    voices = [call["voice"] for call in server.speech_calls]
    assert "。" not in inputs  # no punctuation-only request
    # the trailing 。 merged into the latin run is transliterated so the
    # English voice still produces a pause
    assert inputs == ["我在学习", "HSK. "]
    assert voices == ["zf_xiaobei", "af_heart"]


# ---- extract_json unit cases ----


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('["a", "b"]', ["a", "b"]),
        ('{"k": 1}', {"k": 1}),
        ('```json\n{"k": 2}\n```', {"k": 2}),
        ('```\n[1, 2]\n```', [1, 2]),
        ('Sure! Here is the result: {"pinyin": "nǐ"} hope it helps', {"pinyin": "nǐ"}),
        ('text before [1, 2] and {"a": "}"} after', [1, 2]),
    ],
)
def test_extract_json(text, expected):
    assert extract_json(text) == expected


def test_extract_json_nested_braces_in_strings():
    text = 'The answer is {"code": "if (a) {b}"}.'
    assert extract_json(text) == {"code": "if (a) {b}"}


def test_extract_json_failure():
    with pytest.raises(LlmError):
        extract_json("no json here at all")
