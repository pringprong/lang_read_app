# Smoke Checklist (per milestone)

Manual checks run after each milestone's automated tests pass.
Environment note: tests run with `QT_QPA_PLATFORM=offscreen` when there is no
display; the app itself runs on the real desktop session.

## M0 — Scaffolding

- [x] `pytest` passes (app config paths, main-menu construction).
- [x] Window constructs with the 8 menu options from requirements §12.1 (offscreen).
- [x] Clicking any option shows the "not implemented yet" dialog.
- [x] Data directory is created at `~/.local/share/LangReadApp` on Linux.
- [x] `LANGREAD_DATA_DIR` override works (used by tests).
- [ ] `langread` command launches a **visible** window on the real display —
      blocked on missing system package `libxcb-cursor0` (Qt 6.5+ requirement):
      run `sudo apt install libxcb-cursor0`, then `.venv/bin/langread`.

Environment notes:
- PyPI mirror: Tsinghua returned HTTP 403; switched to **Aliyun**
  (`~/.config/pip/pip.conf` → `https://mirrors.aliyun.com/pypi/simple/`).
- Run tests with `QT_QPA_PLATFORM=offscreen .venv/bin/pytest`.

## M1 — Data layer

- [x] `pytest` passes: 31 tests (topics, lessons, sentences, words, HSK, settings, reviews, templates, migrations).
- [x] Schema applies automatically on first `connect()` (schema_migrations version 1).
- [x] Topic deletion blocked while non-empty (D-9); duplicate topic names rejected.
- [x] Lesson → sentences / lesson_words / review_events cascade delete (FK ON DELETE CASCADE).
- [x] Word `get_or_create` is idempotent — existing list membership wins (§5.1).
- [x] Moving a word between lists syncs its linked HSK entry's `app_state`.
- [x] New-word suggestions: topic-associated first, then oldest-added (D-11).
- [x] Due-word suggestions: same-topic first, then by `due_at` (§7.2).
- [x] HSK import is idempotent; per-level listing/filtering/pagination works.
- [x] Prompt templates seeded from bundled JSON; get/upsert round-trips.

## M2 — SRS engine

- [ ] (pending)
