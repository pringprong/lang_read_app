"""M9 tests: sync bundles — export, verification, results import (§10 / D-3)."""

from __future__ import annotations

import json
import zipfile

import pytest

from langread.db import connect
from langread.db.repositories import LessonsRepo, TemplatesRepo, TopicsRepo, WordsRepo
from langread.services.generation import LessonDraft, GeneratedParagraph
from langread.services.lesson_saver import LessonSaver
from langread.services.srs import SrsService
from langread.services.sync import SyncService, SyncError, write_results_bundle
from tests.integration.test_generation import NEW, REVIEW
from tests.integration.test_lesson_saver import TranslationStub, TtsStub


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("LANGREAD_DATA_DIR", str(tmp_path / "appdata"))
    conn = connect(tmp_path / "test.db")
    TemplatesRepo(conn).seed_defaults()
    topic = TopicsRepo(conn).create("Cooking")
    words = WordsRepo(conn)
    srs = SrsService(conn)
    for text in NEW:
        words.get_or_create(text, list_state="new", source="manual")
    for text in REVIEW:
        word, _ = words.get_or_create(text, list_state="new", source="manual")
        srs.promote_word(word.id, now="2026-11-01T00:00:00+00:00")
    paragraphs = [
        GeneratedParagraph(index=i, text=f"我们学{NEW[i]}。",
                           sentences=[f"我们学{NEW[i]}。"],
                           segmentations=[[f"我们学{NEW[i]}。"]])
        for i in range(3)
    ]
    draft = LessonDraft(topic_id=topic.id, topic_name=topic.name,
                        new_words=list(NEW), review_words=list(REVIEW),
                        paragraphs=paragraphs)
    audio_dir = tmp_path / "appdata" / "audio"
    backups_dir = tmp_path / "appdata" / "backups"
    lesson = LessonSaver(conn, tts=TtsStub(), translation=TranslationStub(),
                         audio_dir=audio_dir).save_lesson(draft)
    yield {
        "conn": conn, "lesson_id": lesson.id, "audio_dir": audio_dir,
        "backups_dir": backups_dir, "tmp_path": tmp_path,
    }
    conn.close()


def _sync(env) -> SyncService:
    return SyncService(env["conn"], audio_dir=env["audio_dir"],
                       backups_dir=env["backups_dir"])


# ---- export ----


def test_export_creates_verified_bundle_with_audio(env):
    stats = _sync(env).export_bundle(env["tmp_path"] / "sync.zip")
    assert stats.lessons == 1
    assert stats.audio_files == 1
    assert stats.words == len(NEW) + len(REVIEW)

    with zipfile.ZipFile(stats.path) as zf:
        names = set(zf.namelist())
    assert {"manifest.json", "content.json"} <= names
    if stats.events:
        assert "events.jsonl" in names
    assert any(name.startswith("audio/lesson_") for name in names)

    manifest = SyncService.verify_bundle(stats.path)
    assert manifest["bundle_type"] == "content"
    assert manifest["counts"]["lessons"] == 1
    with zipfile.ZipFile(stats.path) as zf:
        content = json.loads(zf.read("content.json"))
    assert content["topics"][0]["name"] == "Cooking"
    assert any(w["text"] == NEW[0] and w["list_state"] == "learned"
               for w in content["words"])
    assert content["sentences"][0]["segmentation"] == [f"我们学{NEW[0]}。"]


def test_export_events_incremental(env):
    service = _sync(env)
    first = service.export_bundle(env["tmp_path"] / "sync1.zip")
    assert first.events == 0  # no reviews yet

    # a review happens after the first export (clock-independent timestamp)
    from langread.db import utcnow_iso

    event_time = utcnow_iso()
    srs = SrsService(env["conn"])
    word = WordsRepo(env["conn"]).get_by_text(NEW[0])
    srs.rate_word(word.id, "easy", env["lesson_id"], now=event_time)

    second = service.export_bundle(env["tmp_path"] / "sync2.zip")
    assert second.events == 1  # only the new event (since last export)


# ---- verification ----


def test_verify_rejects_tampered_content(env):
    path = _sync(env).export_bundle(env["tmp_path"] / "sync.zip").path
    # rebuild the zip with modified content.json (checksum mismatch)
    tampered = env["tmp_path"] / "tampered.zip"
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(tampered, "w") as dst:
        for name in src.namelist():
            data = src.read(name)
            if name == "content.json":
                data = data.replace(b"Cooking", b"Hacking")
            dst.writestr(name, data)
    with pytest.raises(SyncError, match="checksum mismatch"):
        SyncService.verify_bundle(tampered)


def test_verify_rejects_missing_manifest_and_bad_zip(env):
    empty = env["tmp_path"] / "empty.zip"
    with zipfile.ZipFile(empty, "w") as zf:
        zf.writestr("content.json", b"{}")
    with pytest.raises(SyncError, match="no manifest"):
        SyncService.verify_bundle(empty)
    not_zip = env["tmp_path"] / "not.zip"
    not_zip.write_text("hello")
    with pytest.raises(SyncError, match="not a valid zip"):
        SyncService.verify_bundle(not_zip)


def test_verify_rejects_wrong_bundle_type(env):
    path = _sync(env).export_bundle(env["tmp_path"] / "sync.zip").path
    with pytest.raises(SyncError, match="results"):
        SyncService.verify_bundle(path, expected_type="results")


# ---- results import ----


def test_import_results_applies_android_reviews(env):
    conn = env["conn"]
    words = WordsRepo(conn)
    srs = SrsService(conn)
    word_a = words.get_by_text(NEW[0])       # learned
    word_b = words.get_by_text(NEW[1])       # learned
    word_b_interval_before = word_b.interval_days

    records = [
        {"type": "rating", "lesson_id": env["lesson_id"], "word_id": word_a.id,
         "rating": "difficult", "reviewed_at": "2026-11-03T10:00:00+00:00"},
        {"type": "rating", "lesson_id": env["lesson_id"], "word_id": word_b.id,
         "rating": "unchanged", "reviewed_at": "2026-11-03T10:00:01+00:00"},
        {"type": "lesson_reviewed", "lesson_id": env["lesson_id"],
         "reviewed_at": "2026-11-03T10:00:02+00:00"},
        {"type": "word_action", "word_text": "我们", "action": "add_new",
         "acted_at": "2026-11-03T10:00:03+00:00"},
    ]
    bundle = write_results_bundle(env["tmp_path"] / "results.zip", records)
    stats = _sync(env).import_results(bundle)

    assert stats.ratings_applied == 2
    assert stats.lessons_marked == 1
    assert stats.word_actions == 1
    # android events are in the append-only log
    android = [e for e in srs.reviews.events_for_lesson(env["lesson_id"])
               if e.device == "android"]
    assert len(android) == 3  # two ratings + one lesson_reviewed
    # difficult applied with the android timestamp
    word_a_after = words.get_by_text(NEW[0])
    assert word_a_after.interval_days == 0.5
    assert word_a_after.last_rated_at == "2026-11-03T10:00:00+00:00"
    # "unchanged" leaves the SRS state alone
    assert words.get_by_text(NEW[1]).interval_days == word_b_interval_before
    # lesson marked reviewed with the android timestamp
    lesson = LessonsRepo(conn).get(env["lesson_id"])
    assert lesson.last_reviewed_at == "2026-11-03T10:00:02+00:00"
    # word action applied
    assert words.get_by_text("我们").list_state == "new"
    # automatic backup was taken before applying
    assert stats.backup_path.exists()
    assert list(env["backups_dir"].glob("pre-import-*.db")) == [stats.backup_path]


def test_import_most_recent_wins(env):
    conn = env["conn"]
    words = WordsRepo(conn)
    srs = SrsService(conn)
    word = words.get_by_text(NEW[0])
    # desktop rating is NEWER than the android event → android rating skipped
    srs.rate_word(word.id, "easy", env["lesson_id"],
                  now="2026-11-10T00:00:00+00:00")
    interval_after_desktop = words.get_by_text(word.text).interval_days

    records = [
        {"type": "rating", "lesson_id": env["lesson_id"], "word_id": word.id,
         "rating": "difficult", "reviewed_at": "2026-11-03T00:00:00+00:00"},
    ]
    bundle = write_results_bundle(env["tmp_path"] / "results.zip", records)
    stats = _sync(env).import_results(bundle)

    assert stats.ratings_applied == 0
    assert stats.ratings_skipped == 1
    assert words.get_by_text(word.text).interval_days == interval_after_desktop
    # the android event is still recorded in the log even though skipped
    android = [e for e in srs.reviews.events_for_lesson(env["lesson_id"])
               if e.device == "android"]
    assert len(android) == 1


def test_import_corrupt_bundle_rejected_before_any_changes(env):
    conn = env["conn"]
    words = WordsRepo(conn)
    word = words.get_by_text(NEW[0])
    records = [
        {"type": "rating", "lesson_id": env["lesson_id"], "word_id": word.id,
         "rating": "easy", "reviewed_at": "2026-11-03T00:00:00+00:00"},
    ]
    bundle = write_results_bundle(env["tmp_path"] / "results.zip", records)
    # tamper with the events payload
    with zipfile.ZipFile(bundle) as src, zipfile.ZipFile(
        env["tmp_path"] / "bad.zip", "w"
    ) as dst:
        for name in src.namelist():
            data = src.read(name)
            if name == "events.jsonl":
                data = data.replace(b"easy", b"difficult")
            dst.writestr(name, data)

    lesson_before = LessonsRepo(conn).get(env["lesson_id"]).last_reviewed_at
    interval_before = word.interval_days
    with pytest.raises(SyncError):
        _sync(env).import_results(env["tmp_path"] / "bad.zip")
    # nothing applied, no backup created
    assert words.get_by_text(NEW[0]).interval_days == interval_before
    assert LessonsRepo(conn).get(env["lesson_id"]).last_reviewed_at == lesson_before
    assert not list(env["backups_dir"].glob("pre-import-*.db"))


def test_import_rejects_content_bundle_as_results(env):
    path = _sync(env).export_bundle(env["tmp_path"] / "sync.zip").path
    with pytest.raises(SyncError, match="results"):
        _sync(env).import_results(path)

