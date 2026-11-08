#!/usr/bin/env python3
"""Verify an Android-produced results bundle against the REAL desktop
SyncService.import_results (the A5/A6 cross-app round-trip check, plan §8).

Usage:
  cd /home/pringprong/android_app
  /home/pringprong/lang_read_app/.venv/bin/python tool/verify_results_bundle.py \\
      build/results-roundtrip.zip
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixture_db import build_fixture, temp_workspace  # noqa: E402

from langread.db.repositories import LessonsRepo, ReviewsRepo, WordsRepo  # noqa: E402
from langread.services.sync import SyncService  # noqa: E402


def read_events(bundle: Path) -> list[dict]:
    with zipfile.ZipFile(bundle) as zf:
        return [json.loads(line) for line in
                zf.read("events.jsonl").decode("utf-8").splitlines()
                if line.strip()]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    bundle = Path(sys.argv[1])
    if not bundle.exists():
        print(f"bundle does not exist: {bundle}")
        return 2

    ws, db_path, audio_dir, backups_dir = temp_workspace()
    fixture = build_fixture(db_path, audio_dir)
    conn = fixture["conn"]
    lesson1 = fixture["lessons"]["first"]

    svc = SyncService(conn, audio_dir=audio_dir, backups_dir=backups_dir)
    stats = svc.import_results(bundle)
    print(f"imported: ratings_applied={stats.ratings_applied} "
          f"ratings_skipped={stats.ratings_skipped} "
          f"lessons_marked={stats.lessons_marked} "
          f"word_actions={stats.word_actions}")

    reviews = ReviewsRepo(conn)
    words = WordsRepo(conn)
    lessons = LessonsRepo(conn)
    failures: list[str] = []

    expected_events = read_events(bundle)
    ratings = [e for e in expected_events if e.get("type") == "rating"]
    lesson_reviews = [e for e in expected_events
                      if e.get("type") == "lesson_reviewed"]
    word_actions = [e for e in expected_events if e.get("type") == "word_action"]

    # 1. every rating event produced a device='android' review_event row
    android_events = [e for e in reviews.events_for_lesson(lesson1.id)
                      if e.device == "android"]
    android_ratings = [e for e in android_events if e.rating is not None]
    if len(android_ratings) != len(ratings):
        failures.append(
            f"expected {len(ratings)} android rating events, "
            f"found {len(android_ratings)}")

    # 2. lesson review timestamp updated (most recent wins)
    lesson = lessons.get(lesson1.id)
    if lesson is None or lesson.last_reviewed_at is None:
        failures.append("lesson.last_reviewed_at was not set")
    for e in lesson_reviews:
        if lesson is None or (lesson.last_reviewed_at or "") < e["reviewed_at"]:
            failures.append(
                f"lesson review timestamp {lesson.last_reviewed_at if lesson else None} "
                f"older than event {e['reviewed_at']}")

    # 3. word actions applied
    for e in word_actions:
        action, text = e.get("action"), e.get("word_text", "")
        word = words.get_by_text(text)
        expect_state = {"add_new": "new", "add_basic": "basic",
                        "basic_to_new": "new"}.get(action)
        if word is None:
            failures.append(f"word_action {action}: word {text!r} not created")
        elif expect_state and word.list_state != expect_state:
            failures.append(
                f"word_action {action}: {text!r} state "
                f"{word.list_state!r} != {expect_state!r}")

    # 4. SRS materialized for rated learned words (most recent wins)
    for e in ratings:
        word = words.get(e.get("word_id"))
        if word is None:
            failures.append(f"rating event for unknown word {e.get('word_id')}")
        elif word.list_state == "learned" and word.last_rated_at is None:
            failures.append(f"word {word.text!r} not rated after import")

    if failures:
        print("ROUND-TRIP FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"ROUND-TRIP OK: {len(expected_events)} events "
          f"({len(ratings)} ratings, {len(lesson_reviews)} lesson reviews, "
          f"{len(word_actions)} word actions) all applied correctly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
