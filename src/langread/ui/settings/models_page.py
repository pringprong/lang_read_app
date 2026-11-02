"""Model endpoints settings page (requirements §9.1, §12.1 item 6)."""

from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from langread.db.repositories import SettingsRepo
from langread.services.model_settings import MODEL_SERVICES, ModelSettings
from langread.ui.workers import run_async


class _LlmGroup(QGroupBox):
    def __init__(self, prefix: str, label: str, settings: ModelSettings,
                 parent: QWidget | None = None) -> None:
        super().__init__(label, parent)
        self.prefix = prefix
        self.settings = settings

        self.base_url = QLineEdit()
        self.base_url.setPlaceholderText("http://192.168.1.20:1234/v1")
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("(optional for local servers)")
        self.model = QLineEdit()
        self.model.setPlaceholderText("model name as served by the endpoint")

        form = QFormLayout(self)
        form.addRow("Base URL:", self.base_url)
        form.addRow("API key:", self.api_key)
        form.addRow("Model:", self.model)

        self.test_button = QPushButton("Test connection")
        self.test_button.clicked.connect(self._test)
        form.addRow("", self.test_button)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        form.addRow("", self.status)

        self._worker = None
        self._load()

    def _load(self) -> None:
        values = self.settings.get(self.prefix)
        self.base_url.setText(str(values.get("base_url") or ""))
        self.api_key.setText(str(values.get("api_key") or ""))
        self.model.setText(str(values.get("model") or ""))

    def save(self) -> None:
        self.settings.save(
            self.prefix,
            {"base_url": self.base_url.text(), "api_key": self.api_key.text(),
             "model": self.model.text()},
        )

    def _test(self) -> None:
        self.save()
        # resolve the config on the UI thread (SQLite connections are
        # thread-bound); the worker only performs the network call
        from langread.services.model_settings import ModelSettingsError

        try:
            config = self.settings.llm_config(self.prefix)
        except ModelSettingsError as exc:
            self.status.setText(f"❌ {exc}")
            return
        self.test_button.setEnabled(False)
        self.status.setText("Testing…")
        from langread.services.llm_client import LlmClient

        self._worker = run_async(
            lambda: LlmClient(config).chat(
                "Reply with exactly: OK", temperature=0.0
            ),
            self._on_test_done,
            self,
        )

    def _on_test_done(self, result, error) -> None:
        self.test_button.setEnabled(True)
        self.status.setText(
            f"❌ {error}" if error is not None
            else f"✅ Connected — model replied: {result!r}"
        )


class _TtsGroup(QGroupBox):
    def __init__(self, settings: ModelSettings,
                 parent: QWidget | None = None) -> None:
        super().__init__("Text-to-speech model (Kokoro)", parent)
        self.settings = settings

        self.base_url = QLineEdit()
        self.base_url.setPlaceholderText("http://192.168.1.20:8880/v1")
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.model = QLineEdit()
        self.model.setPlaceholderText("e.g. kokoro")
        self.voice = QLineEdit()
        self.voice.setPlaceholderText("Chinese voice name, e.g. zf_xiaobei")
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0.5, 2.0)
        self.speed.setSingleStep(0.05)
        self.speed.setValue(1.0)

        form = QFormLayout(self)
        form.addRow("Base URL:", self.base_url)
        form.addRow("API key:", self.api_key)
        form.addRow("Model:", self.model)
        form.addRow("Voice:", self.voice)
        form.addRow("Speed:", self.speed)

        self.test_button = QPushButton("Test connection")
        self.test_button.clicked.connect(self._test)
        form.addRow("", self.test_button)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        form.addRow("", self.status)

        self._worker = None
        self._load()

    def _load(self) -> None:
        values = self.settings.get("tts")
        self.base_url.setText(str(values.get("base_url") or ""))
        self.api_key.setText(str(values.get("api_key") or ""))
        self.model.setText(str(values.get("model") or ""))
        self.voice.setText(str(values.get("voice") or ""))
        speed = values.get("speed")
        self.speed.setValue(float(speed) if speed not in (None, "") else 1.0)

    def save(self) -> None:
        self.settings.save(
            "tts",
            {"base_url": self.base_url.text(), "api_key": self.api_key.text(),
             "model": self.model.text(), "voice": self.voice.text(),
             "speed": self.speed.value()},
        )

    def _test(self) -> None:
        self.save()
        # resolve the config on the UI thread (SQLite connections are
        # thread-bound); the worker only performs the network call
        from langread.services.model_settings import ModelSettingsError

        try:
            config = self.settings.tts_config()
        except ModelSettingsError as exc:
            self.status.setText(f"❌ {exc}")
            return
        self.test_button.setEnabled(False)
        self.status.setText("Testing…")
        from langread.services.tts import TtsService

        self._worker = run_async(
            lambda: len(TtsService(config).synthesize("你好")),
            self._on_test_done,
            self,
        )

    def _on_test_done(self, result, error) -> None:
        self.test_button.setEnabled(True)
        self.status.setText(
            f"❌ {error}" if error is not None
            else f"✅ Received {result} bytes of MP3 audio."
        )


class ModelsPage(QWidget):
    """All three model endpoint configurations with test buttons."""

    def __init__(self, conn: sqlite3.Connection,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = ModelSettings(SettingsRepo(conn))

        layout = QVBoxLayout(self)
        self._groups: list[QGroupBox] = []
        for prefix, (label, kind) in MODEL_SERVICES.items():
            group = (
                _TtsGroup(self.settings)
                if kind == "tts"
                else _LlmGroup(prefix, label, self.settings)
            )
            layout.addWidget(group)
            self._groups.append(group)
        layout.addStretch(1)

    def save(self) -> None:
        for group in self._groups:
            group.save()

