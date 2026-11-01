"""M3 integration tests: LLM + TTS clients against the fake server."""

from __future__ import annotations

import pytest

from langread.services.llm_client import LlmClient, LlmConfig, LlmError, extract_json
from langread.services.tts import TtsConfig, TtsError, TtsService, looks_like_mp3

from tests.fakes.openai_server import FakeOpenAiServer


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
