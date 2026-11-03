"""Audio playback bar (requirements §8.5, D-1).

Pure audio controls: play/pause, restart, speed 0.5×–2×, ±15 seconds, and
"jump to the end" (which just stops the audio — moving on to the word
review is an explicit user action via the reading page's button, since the
user typically listens several times before continuing).

If the platform's audio backend is unavailable the bar degrades gracefully.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

SPEEDS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
JUMP_MS = 15_000


class AudioBar(QWidget):
    def __init__(self, audio_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._player = None
        self._audio_output = None
        self._error: str | None = None

        if audio_path is not None and Path(audio_path).exists():
            try:
                from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

                self._player = QMediaPlayer(self)
                self._audio_output = QAudioOutput(self)
                self._player.setAudioOutput(self._audio_output)
                self._player.setSource(_to_url(audio_path))
                self._player.mediaStatusChanged.connect(self._on_status)
            except Exception as exc:  # missing multimedia backend
                self._error = str(exc)
        else:
            self._error = "audio file not found"

        self.play_button = QPushButton("▶ Play")
        self.play_button.clicked.connect(self._play_pause)
        self.restart_button = QPushButton("⟲ Restart")
        self.restart_button.clicked.connect(self._restart)
        self.back_button = QPushButton("−15s")
        self.back_button.clicked.connect(lambda: self._seek(-JUMP_MS))
        self.forward_button = QPushButton("+15s")
        self.forward_button.clicked.connect(lambda: self._seek(JUMP_MS))
        self.speed_combo = QComboBox()
        for speed in SPEEDS:
            self.speed_combo.addItem(f"{speed:g}×", speed)
        self.speed_combo.setCurrentIndex(SPEEDS.index(1.0))
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        self.end_button = QPushButton("Jump to end")
        self.end_button.setToolTip("Stop the audio at its end")
        self.end_button.clicked.connect(self._jump_to_end)
        self.status = QLabel("")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for widget in (self.play_button, self.restart_button, self.back_button,
                       self.forward_button, self.speed_combo, self.end_button):
            layout.addWidget(widget)
        layout.addStretch(1)
        layout.addWidget(self.status)

        if self._error:
            self.status.setText(f"⚠ audio unavailable: {self._error}")
            for button in (self.play_button, self.restart_button, self.back_button,
                           self.forward_button):
                button.setEnabled(False)

    # ---- controls ----

    def _play_pause(self) -> None:
        if self._player is None:
            return
        from PySide6.QtMultimedia import QMediaPlayer

        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
            self.play_button.setText("▶ Play")
        else:
            self._player.play()
            self.play_button.setText("⏸ Pause")

    def _restart(self) -> None:
        if self._player is None:
            return
        self._player.setPosition(0)
        self._player.play()
        self.play_button.setText("⏸ Pause")

    def _seek(self, offset_ms: int) -> None:
        if self._player is None:
            return
        position = max(0, self._player.position() + offset_ms)
        duration = self._player.duration()
        if duration > 0:
            position = min(position, duration)
        self._player.setPosition(position)

    def _on_speed_changed(self) -> None:
        if self._player is not None:
            self._player.setPlaybackRate(float(self.speed_combo.currentData() or 1.0))

    def _jump_to_end(self) -> None:
        """§8.5: jump to the end (stops playback; no auto-advance)."""
        if self._player is not None:
            duration = self._player.duration()
            if duration > 0:
                self._player.setPosition(duration)
            self._player.stop()
        self.play_button.setText("▶ Play")

    def stop(self) -> None:
        """Stop playback (used when the review window closes by any path)."""
        if self._player is not None:
            self._player.stop()
        self.play_button.setText("▶ Play")

    def _on_status(self, status) -> None:
        from PySide6.QtMultimedia import QMediaPlayer

        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_button.setText("▶ Play")

    # ---- test helpers ----

    def player(self):
        return self._player


def _to_url(audio_path):
    from PySide6.QtCore import QUrl

    return QUrl.fromLocalFile(str(audio_path))

