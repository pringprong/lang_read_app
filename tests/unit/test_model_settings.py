"""M3 unit tests: ModelSettings storage and typed configs."""

from __future__ import annotations

import pytest

from langread.db import connect
from langread.db.repositories import SettingsRepo
from langread.services.llm_client import LlmConfig
from langread.services.model_settings import ModelSettings, ModelSettingsError
from langread.services.tts import TtsConfig


@pytest.fixture()
def repo(tmp_path):
    conn = connect(tmp_path / "test.db")
    yield SettingsRepo(conn)
    conn.close()


@pytest.fixture()
def settings(repo):
    return ModelSettings(repo)


def test_missing_config_raises_helpful_error(settings):
    with pytest.raises(ModelSettingsError, match="gen.base_url"):
        settings.llm_config("gen")


def test_llm_config_roundtrip(settings):
    settings.save("gen", {"base_url": "http://host:1234/v1",
                          "api_key": "sk-1", "model": "qwen"})
    config = settings.llm_config("gen")
    assert isinstance(config, LlmConfig)
    assert config.base_url == "http://host:1234/v1"
    assert config.api_key == "sk-1"
    assert config.model == "qwen"
    assert config.temperature == 0.7  # default when unset


def test_temperature_persisted(settings):
    settings.save("trans", {"base_url": "http://h/v1", "model": "m",
                            "temperature": 0.2})
    assert settings.llm_config("trans").temperature == 0.2


def test_tts_config_roundtrip(settings):
    settings.save("tts", {"base_url": "http://h:8880/v1", "model": "kokoro",
                          "voice": "zf_xiaobei", "speed": 1.25})
    config = settings.tts_config()
    assert isinstance(config, TtsConfig)
    assert config.voice == "zf_xiaobei"
    assert config.speed == 1.25


def test_tts_missing_model_raises(settings):
    settings.save("tts", {"base_url": "http://h/v1"})
    with pytest.raises(ModelSettingsError, match="tts.model"):
        settings.tts_config()


def test_empty_api_key_becomes_none(settings):
    settings.save("gen", {"base_url": "http://h/v1", "model": "m", "api_key": "  "})
    assert settings.llm_config("gen").api_key is None
