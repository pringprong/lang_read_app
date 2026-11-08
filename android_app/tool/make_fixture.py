#!/usr/bin/env python3
"""Generate test/fixtures/sync-v1.zip using the REAL desktop SyncService.

This pins the Android test fixtures to the actual desktop implementation,
not to a hand-written copy of the spec (plan §8).

Usage:
  cd /home/pringprong/android_app
  /home/pringprong/lang_read_app/.venv/bin/python tool/make_fixture.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixture_db import build_fixture, temp_workspace  # noqa: E402

from langread.services.sync import SyncService  # noqa: E402


def main() -> int:
    ws, db_path, audio_dir, backups_dir = temp_workspace()
    fixture = build_fixture(db_path, audio_dir)
    conn = fixture["conn"]

    out = Path(__file__).resolve().parent.parent / "test" / "fixtures" / "sync-v1.zip"
    out.parent.mkdir(parents=True, exist_ok=True)

    svc = SyncService(conn, audio_dir=audio_dir, backups_dir=backups_dir)
    stats = svc.export_bundle(out)

    print(f"exported: {out}")
    print(f"stats: topics={stats.topics} lessons={stats.lessons} "
          f"sentences={stats.sentences} words={stats.words} "
          f"audio={stats.audio_files} events={stats.events}")

    # sanity: the bundle we just wrote must verify
    manifest = SyncService.verify_bundle(out, expected_type="content")
    print(f"verified: schema_version={manifest['schema_version']} "
          f"bundle_type={manifest['bundle_type']} files={len(manifest['files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
