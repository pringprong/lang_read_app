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

- [x] `pytest` passes: 53 total (22 new — rating matrix, clamps, chains, exposure, service).
- [x] Promotion: new → learned with initial interval/ease/due (§7.9.3).
- [x] Ratings: difficult (relearn 0.5d, ease −0.20, lapses+1), easy (×1.3 bonus, ease +0.15, reps+1), standard (×ease, reps+1), unchanged (identity) — §8.6.
- [x] Exposure growth (×ease×multiplier, no reps/event) for words merely used in new lessons — §7.9.4.
- [x] Ease clamped [1.3, 3.0]; growth interval clamped [1, 365] days; relearn step exempt from the min so "difficult" returns sub-day — §8.6.1.
- [x] Parameters persisted in settings (`srs.params`), unknown keys ignored; in-app editor page comes with the settings UI (M3+).
- [x] `rate_word` writes the review event *before* updating SRS; exposure writes no event.

## M3 — Model layer

- [x] `pytest` passes: 78 total (25 new — LLM/TTS clients vs fake server, model settings, JSON extraction, settings UI pages).
- [x] `LlmClient`: OpenAI-compatible chat with defensive JSON extraction (direct / fenced / embedded) + one fix-up retry; network errors wrapped as `LlmError`.
- [x] `TtsService`: `/audio/speech` → MP3 bytes with header validation; `synthesize_to_file`.
- [x] `ModelSettings`: gen/trans/tts settings keys, typed `LlmConfig`/`TtsConfig`, helpful errors when unconfigured, `test_llm`/`test_tts` connection checks.
- [x] Settings dialog with 3 tabs: Models (3 endpoint groups + async Test buttons), Prompt templates (editor + placeholder hints + save), Spaced repetition (all 11 parameters).
- [x] Main menu: "Model settings" and "SRS settings" buttons open the dialog on the right tab; DB connection opened lazily and closed on exit.
- [x] Fake OpenAI-compatible test server (threaded HTTP) drives client integration tests.
- [ ] **User smoke test (real endpoints):** configure LM Studio + Kokoro URLs in the app's Model settings and press "Test connection" on each — deferred until those services are reachable from this laptop.

## M4 — Segmentation

- [ ] (pending)
