"""Model endpoint settings (§9.1) shared by services and the settings UI.

Settings keys (JSON values in the settings table):
  gen.base_url / gen.api_key / gen.model / gen.temperature
  trans.base_url / trans.api_key / trans.model
  tts.base_url / tts.api_key / tts.model / tts.voice / tts.speed
"""

from __future__ import annotations

from dataclasses import dataclass

from langread.db.repositories import SettingsRepo
from langread.services.llm_client import LlmConfig
from langread.services.tts import TtsConfig

# service prefix → (label, kind)
MODEL_SERVICES: dict[str, tuple[str, str]] = {
    "gen": ("Sentence generation model", "llm"),
    "trans": ("Translation model", "llm"),
    "tts": ("Text-to-speech model (Kokoro)", "tts"),
}


class ModelSettingsError(Exception):
    """Raised when a required endpoint setting is missing."""


def _require(values: dict, key: str, prefix: str) -> str:
    value = (values.get(key) or "").strip() if isinstance(values.get(key), str) else values.get(key)
    if not value:
        raise ModelSettingsError(
            f"{prefix}.{key} is not configured (open Model settings to set it)."
        )
    return value


class ModelSettings:
    def __init__(self, repo: SettingsRepo) -> None:
        self.repo = repo

    # ---- raw get/save (used by the settings UI) ----

    def get(self, prefix: str) -> dict:
        """All stored values for a service prefix (missing keys → '')."""
        return {
            key: self.repo.get(f"{prefix}.{key}", default="")
            for key in ("base_url", "api_key", "model", "temperature",
                        "voice", "latin_voice", "speed")
        }

    def save(self, prefix: str, values: dict) -> None:
        for key in ("base_url", "api_key", "model", "voice", "latin_voice"):
            if key in values:
                self.repo.set(f"{prefix}.{key}", str(values[key]).strip())
        if "temperature" in values and values["temperature"] != "":
            self.repo.set(f"{prefix}.temperature", float(values["temperature"]))
        if "speed" in values and values["speed"] != "":
            self.repo.set(f"{prefix}.speed", float(values["speed"]))

    # ---- typed configs (used by the services) ----

    def llm_config(self, prefix: str) -> LlmConfig:
        values = self.get(prefix)
        return LlmConfig(
            base_url=_require(values, "base_url", prefix),
            model=_require(values, "model", prefix),
            api_key=(values.get("api_key") or "").strip() or None,
            temperature=float(values.get("temperature") or 0.7),
        )

    def tts_config(self) -> TtsConfig:
        values = self.get("tts")
        return TtsConfig(
            base_url=_require(values, "base_url", "tts"),
            model=_require(values, "model", "tts"),
            api_key=(values.get("api_key") or "").strip() or None,
            voice=str(values.get("voice") or "").strip() or None,
            latin_voice=str(values.get("latin_voice") or "").strip() or None,
            speed=float(values.get("speed") or 1.0),
        )

    # ---- connection tests (used by the settings UI 'Test' buttons) ----

    def test_llm(self, prefix: str) -> str:
        """Send a tiny ping; returns the model's reply or raises."""
        from langread.services.llm_client import LlmClient

        client = LlmClient(self.llm_config(prefix))
        return client.chat("Reply with exactly: OK", temperature=0.0)

    def test_tts(self) -> int:
        """Synthesize two characters; returns the MP3 byte count or raises."""
        from langread.services.tts import TtsService

        data = TtsService(self.tts_config()).synthesize("你好")
        return len(data)
