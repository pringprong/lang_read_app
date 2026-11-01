"""Desktop ↔ Android sync bundles (requirements §10, D-3; desktop plan §9).

**Content bundle** (desktop → Android): `sync-v1.zip` containing
  - manifest.json  — schema version, counts, SHA-256 of every file
  - content.json   — topics, lessons, sentences, words (incl. SRS state),
                     lesson_words, hsk_words (for offline review)
  - audio/lesson_<id>.mp3 — one file per lesson
  - events.jsonl   — desktop review events since the last export

**Results bundle** (Android → desktop): same integrity scheme, containing
  - manifest.json  — bundle_type "results"
  - events.jsonl   — records: rating / lesson_reviewed / word_action

Import verifies every checksum BEFORE applying anything, and takes an
automatic database backup first, so a bad sync can be rolled back (D-3).
SRS conflicts resolve to the most recent rating by timestamp (§10).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from langread.db import utcnow_iso
from langread.db.repositories import (
    HskRepo,
    LessonsRepo,
    ReviewsRepo,
    SentencesRepo,
    SettingsRepo,
    TopicsRepo,
    WordsRepo,
)
from langread.services.srs import SrsService

BUNDLE_SCHEMA_VERSION = 1
LAST_EXPORT_KEY = "sync.last_export"

_RATINGS = ("difficult", "easy", "standard", "unchanged")
_WORD_ACTIONS = ("add_new", "add_basic", "basic_to_new")


class SyncError(Exception):
    """Bundle verification or application failure."""


@dataclass(frozen=True)
class ExportStats:
    topics: int
    lessons: int
    sentences: int
    words: int
    audio_files: int
    events: int
    path: Path


@dataclass(frozen=True)
class ImportStats:
    ratings_applied: int
    ratings_skipped: int
    lessons_marked: int
    word_actions: int
    backup_path: Path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record_timestamp(record: dict) -> str:
    return record.get("reviewed_at") or record.get("acted_at") or ""


def write_results_bundle(path: Path, records: list[dict]) -> Path:
    """Reference implementation of the results-bundle format (used by tests
    and as the spec for the Android implementation)."""
    events = "\n".join(
        json.dumps(record, ensure_ascii=False) for record in records
    ).encode("utf-8")
    manifest = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_type": "results",
        "created_at": utcnow_iso(),
        "counts": {"events": len(records)},
        "files": {"events.jsonl": _sha256(events)},
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("events.jsonl", events)
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
    return path


class SyncService:
    def __init__(self, conn: sqlite3.Connection, audio_dir: Path | None = None,
                 backups_dir: Path | None = None) -> None:
        self.conn = conn
        self.topics = TopicsRepo(conn)
        self.lessons = LessonsRepo(conn)
        self.sentences = SentencesRepo(conn)
        self.words = WordsRepo(conn)
        self.hsk = HskRepo(conn)
        self.reviews = ReviewsRepo(conn)
        self.settings = SettingsRepo(conn)
        self.srs = SrsService(conn)
        if audio_dir is None:
            from langread.app_config import audio_dir as default_audio_dir

            audio_dir = default_audio_dir()
        if backups_dir is None:
            from langread.app_config import backups_dir as default_backups_dir

            backups_dir = default_backups_dir()
        self._audio_dir = Path(audio_dir)
        self._backups_dir = Path(backups_dir)

    # ---------- content export (desktop → Android) ----------

    def build_content(self) -> dict:
        topics = [
            {"id": t.id, "name": t.name, "order_index": t.order_index,
             "created_at": t.created_at}
            for t in self.topics.list_all()
        ]
        lessons = []
        for topic in self.topics.list_all():
            for lesson in self.lessons.list_for_topic(topic.id):
                lessons.append({
                    "id": lesson.id, "topic_id": lesson.topic_id,
                    "order_index": lesson.order_index, "title": lesson.title,
                    "status": lesson.status, "audio_path": lesson.audio_path,
                    "created_at": lesson.created_at,
                    "last_reviewed_at": lesson.last_reviewed_at,
                })
        sentences = []
        for lesson in lessons:
            for sentence in self.sentences.list_for_lesson(lesson["id"]):
                sentences.append({
                    "id": sentence.id, "lesson_id": sentence.lesson_id,
                    "para_index": sentence.para_index,
                    "sent_index": sentence.sent_index, "text": sentence.text,
                    "segmentation": sentence.segmentation,
                    "translation": sentence.translation,
                })
        words = [
            {"id": w.id, "text": w.text, "pinyin": w.pinyin,
             "definition": w.definition, "list_state": w.list_state,
             "hsk_word_id": w.hsk_word_id, "source": w.source,
             "added_at": w.added_at, "ease": w.ease,
             "interval_days": w.interval_days, "due_at": w.due_at,
             "reps": w.reps, "lapses": w.lapses,
             "last_rated_at": w.last_rated_at}
            for state in ("new", "learned", "basic")
            for w in self.words.list_by_state(state)
        ]
        lesson_words = [
            {"lesson_id": lesson_id, "word_id": word_id, "role": role}
            for lesson_id, word_id, role in _all_lesson_words(self.conn)
        ]
        hsk_words = [
            {"id": h.id, "text": h.text, "pinyin": h.pinyin,
             "definition": h.definition, "level": h.level,
             "app_state": h.app_state}
            for h in self.hsk.list_all()
        ]
        return {
            "schema_version": BUNDLE_SCHEMA_VERSION,
            "exported_at": utcnow_iso(),
            "topics": topics,
            "lessons": lessons,
            "sentences": sentences,
            "words": words,
            "lesson_words": lesson_words,
            "hsk_words": hsk_words,
        }

    def export_bundle(self, out_path: Path) -> ExportStats:
        """Write a content bundle; the written bundle is re-verified before
        the export is recorded (D-3 data integrity)."""
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        content = self.build_content()
        last_export = self.settings.get(LAST_EXPORT_KEY, default="")
        events = self.reviews.events_since(str(last_export or ""))
        events_payload = "\n".join(
            json.dumps({
                "type": "rating" if e.rating else "lesson_reviewed",
                "lesson_id": e.lesson_id, "word_id": e.word_id,
                "rating": e.rating, "reviewed_at": e.reviewed_at,
                "device": e.device,
            }, ensure_ascii=False)
            for e in events
        ).encode("utf-8")

        audio_files: list[tuple[str, Path]] = []
        for lesson in content["lessons"]:
            if lesson["audio_path"]:
                source = self._audio_dir / lesson["audio_path"]
                if source.exists():
                    audio_files.append((f"audio/{lesson['audio_path']}", source))

        content_bytes = json.dumps(content, ensure_ascii=False).encode("utf-8")
        files: dict[str, str] = {"content.json": _sha256(content_bytes)}
        if events_payload.strip():
            files["events.jsonl"] = _sha256(events_payload)
        for arcname, source in audio_files:
            files[arcname] = _sha256(source.read_bytes())

        manifest = {
            "schema_version": BUNDLE_SCHEMA_VERSION,
            "bundle_type": "content",
            "created_at": utcnow_iso(),
            "counts": {
                "topics": len(content["topics"]),
                "lessons": len(content["lessons"]),
                "sentences": len(content["sentences"]),
                "words": len(content["words"]),
                "lesson_words": len(content["lesson_words"]),
                "hsk_words": len(content["hsk_words"]),
                "audio_files": len(audio_files),
                "events": len(events),
            },
            "files": files,
        }

        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("content.json", content_bytes)
            if events_payload.strip():
                zf.writestr("events.jsonl", events_payload)
            for arcname, source in audio_files:
                zf.write(source, arcname)
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))

        # verify what we just wrote before recording the export
        self.verify_bundle(out_path, expected_type="content")
        self.settings.set(LAST_EXPORT_KEY, utcnow_iso())

        return ExportStats(
            topics=len(content["topics"]), lessons=len(content["lessons"]),
            sentences=len(content["sentences"]), words=len(content["words"]),
            audio_files=len(audio_files), events=len(events), path=out_path,
        )

    # ---------- verification ----------

    @staticmethod
    def verify_bundle(path: Path, expected_type: str | None = None) -> dict:
        """Verify a bundle's manifest and every file checksum.
        Returns the manifest; raises SyncError on any problem."""
        path = Path(path)
        if not path.exists():
            raise SyncError(f"bundle does not exist: {path}")
        try:
            with zipfile.ZipFile(path) as zf:
                names = set(zf.namelist())
                if "manifest.json" not in names:
                    raise SyncError("bundle has no manifest.json")
                manifest = json.loads(zf.read("manifest.json"))
                if manifest.get("schema_version") != BUNDLE_SCHEMA_VERSION:
                    raise SyncError(
                        f"unsupported bundle schema version "
                        f"{manifest.get('schema_version')!r} "
                        f"(expected {BUNDLE_SCHEMA_VERSION})"
                    )
                if expected_type and manifest.get("bundle_type") != expected_type:
                    raise SyncError(
                        f"expected a {expected_type!r} bundle, "
                        f"got {manifest.get('bundle_type')!r}"
                    )
                for name, digest in manifest.get("files", {}).items():
                    if name not in names:
                        raise SyncError(f"manifest lists missing file: {name}")
                    if _sha256(zf.read(name)) != digest:
                        raise SyncError(f"checksum mismatch for {name}")
                return manifest
        except zipfile.BadZipFile as exc:
            raise SyncError(f"not a valid zip bundle: {exc}") from exc

    # ---------- results import (Android → desktop) ----------

    def import_results(self, bundle_path: Path) -> ImportStats:
        """Verify, back up, then apply an Android results bundle (§10)."""
        self.verify_bundle(bundle_path, expected_type="results")
        with zipfile.ZipFile(bundle_path) as zf:
            raw = zf.read("events.jsonl").decode("utf-8")
        records = [json.loads(line) for line in raw.splitlines() if line.strip()]
        records.sort(key=_record_timestamp)

        # automatic backup BEFORE anything is applied (D-3)
        self._backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = utcnow_iso().replace(":", "")
        backup_path = self._backups_dir / f"pre-import-{stamp}.db"
        with sqlite3.connect(backup_path) as destination:
            self.conn.backup(destination)

        ratings_applied = ratings_skipped = lessons_marked = word_actions = 0
        for record in records:
            kind = record.get("type")
            if kind == "rating":
                word_id = record.get("word_id")
                lesson_id = record.get("lesson_id")
                rating = record.get("rating")
                reviewed_at = record.get("reviewed_at") or utcnow_iso()
                if rating not in _RATINGS:
                    continue
                self.reviews.add(
                    lesson_id=lesson_id, word_id=word_id, rating=rating,
                    device="android", reviewed_at=reviewed_at,
                )
                word = self.words.get(word_id) if word_id is not None else None
                if (word is not None and word.list_state == "learned"
                        and (word.last_rated_at is None
                             or reviewed_at > word.last_rated_at)):
                    # most recent rating wins (§10 conflict rule)
                    self.srs.apply_rating_at(word_id, rating, reviewed_at)
                    ratings_applied += 1
                else:
                    ratings_skipped += 1
            elif kind == "lesson_reviewed":
                lesson_id = record.get("lesson_id")
                reviewed_at = record.get("reviewed_at") or utcnow_iso()
                lesson = self.lessons.get(lesson_id) if lesson_id is not None else None
                if lesson is None:
                    continue
                self.reviews.add(
                    lesson_id=lesson_id, word_id=None, rating=None,
                    device="android", reviewed_at=reviewed_at,
                )
                if (lesson.last_reviewed_at is None
                        or reviewed_at > lesson.last_reviewed_at):
                    self.lessons.mark_reviewed(lesson_id, reviewed_at)
                    lessons_marked += 1
            elif kind == "word_action":
                action = record.get("action")
                text = (record.get("word_text") or "").strip()
                if not text or action not in _WORD_ACTIONS:
                    continue
                if action == "add_new":
                    self.words.get_or_create(text, list_state="new",
                                             source="lesson")
                elif action == "add_basic":
                    self.words.get_or_create(text, list_state="basic",
                                             source="lesson")
                else:  # basic_to_new
                    word = self.words.get_by_text(text)
                    if word is not None and word.list_state == "basic":
                        self.words.move_to_state(word.id, "new")
                word_actions += 1
        return ImportStats(
            ratings_applied=ratings_applied, ratings_skipped=ratings_skipped,
            lessons_marked=lessons_marked, word_actions=word_actions,
            backup_path=backup_path,
        )


def _all_lesson_words(conn: sqlite3.Connection) -> list[tuple[int, int, str]]:
    rows = conn.execute(
        "SELECT lesson_id, word_id, role FROM lesson_words ORDER BY lesson_id, word_id"
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]



