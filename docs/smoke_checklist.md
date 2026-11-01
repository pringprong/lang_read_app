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

- [x] `pytest` passes: 96 total (18 new — segmentation service + editor widget).
- [x] jieba with custom dictionary from app word lists + HSK (app words segment atomically, `refresh_dictionary()` after list changes).
- [x] Tokens resolve to word-list entries (word_id/list_state/pinyin/definition), HSK-only entries, or unresolved.
- [x] Punctuation separated into its own non-CJK tokens.
- [x] LLM fallback when a multi-char token is unknown to both the app and jieba's dictionary; fallback result validated (same CJK characters) or rejected; LLM errors fall back to jieba silently.
- [x] `SegmentationEditor` widget: chips UI, merge selected (contiguous runs), split into characters, reset; `changed` signal.
- [x] Dependencies added: jieba 0.42.1, pypinyin 0.55.0.

## M5 — Word lists & HSK

- [x] `pytest` passes: 116 total (20 new — HSK service, word import flows, UI flows).
- [x] **HSK dataset bundled** (D-7): 4,991 words (150/147/298/598/1298/2500 per level, words deduped to their lowest level) from `drkameleon/complete-hsk-vocabulary` (MIT license; old HSK standard, CC-CEDICT definitions), downloaded via jsDelivr/gcore CDNs (raw.githubusercontent is blocked on this network), normalized by `scripts/build_hsk_csv.py` into `resources/hsk/hsk.csv`.
- [x] HSK auto-imported into the DB on first word-related use (`HskService.import_if_needed`).
- [x] Paste-import flow (§5.1): parse pasted text → distinct words with status (existing list / HSK level / unknown) → tick new words → marked→New, rest→Basic, existing membership wins; HSK linking + topic association.
- [x] Manual entry (§5.2), HSK→New/Basic add with pinyin/definition (§5.5), Basic→New and New→Basic moves (§5.4).
- [x] Word-list manager UI: 4 tabs (New with topic assignment, Learned with SRS info, Basic, HSK browser with level filter, unused-only filter, multi-select bulk add).
- [x] Bug fixed during M5: HSK import must run **before** the segmentation dictionary loads, otherwise words like 喝咖啡 mis-segment; dictionary version check now per-list counts.
- [x] Main-menu buttons "Add new words" (3) and "Manage word lists" (4) wired.

## M6 — Lesson creation

- [x] `pytest` passes: 136 total (20 new — cadence planner, generation pipeline, wizard UI).
- [x] `services/cadence.py`: pure planner — one first-use new word per paragraph (§6.2), none in the final paragraph, final paragraph uses all new words (§6.4), repeats prefer lowest-usage words (§6.3), review rotation, usage tracking (§7.6). Validation: 5–10 new words, paragraphs > new words (wizard allows up to 12 paragraphs; documented deviation for 9–10-word lessons).
- [x] `services/generation.py`: paragraph-at-a-time generation (D-12) from editable templates, unknown-placeholder validation, LLM reply cleaning (fences/quotes/labels), sentence splitting, per-sentence segmentation, usage check + ≤2 retries with "MUST contain the word" fix-up (§7.6), progress callback, `LessonDraft` result.
- [x] Wizard UI (3 steps): word selection with suggestions (D-11/§7.2) + validation; background generation with live progress; final review page with per-paragraph text editing (re-split + re-segment) and per-sentence segmentation merge/split (D-6); "Change words → regenerate all" (§7.8).
- [x] Topic creation from the main menu; "Create a new lesson" picks a topic, wires the real generation LLM from Model settings (with a clear error when unconfigured).
- [x] Threading fix: `GenerationWorker` opens its **own SQLite connection** (connections are thread-bound); UI updated via queued signals.
- [ ] "Approve & save" shows an M7 placeholder — the save pipeline (TTS, translations, promotion, SRS, persistence) is next.

## M7 — Save pipeline

- [x] `pytest` passes: 149 total (13 new — translation service, save pipeline, end-to-end wizard save).
- [x] `services/translation.py`: sentence translation + word pinyin/definition via templates; **pypinyin offline fallback** for pinyin; tolerant of bad JSON (returns None rather than failing).
- [x] `TtsService.synthesize_texts_to_file`: per-paragraph synthesis (avoids request-size limits) concatenated into the single lesson MP3 (D-1).
- [x] `services/lesson_saver.py` (§7.9): lesson + sentences + lesson_words creation → translations → word promotion (pinyin/definition + HSK linking + New→Learned with initial SRS) → review-word SRS exposure → audio → complete.
- [x] **Resumable**: every step idempotent; an interrupted save leaves `status='incomplete'` and `finalize_lesson` completes it without duplicating or re-exposing.
- [x] TTS is required (clear `SaveError` when unconfigured); translation is optional (sentences stay NULL, words fall back to pypinyin).
- [x] Wizard "Approve && save" runs `SaveWorker` in a background thread (own DB connection) with stage progress; failure keeps the lesson incomplete with a re-approve hint.
- [x] End-to-end test: wizard → generation → approve → saved lesson with audio, driven by the fake OpenAI-compatible server for TTS + translation.

## M8 — Review UI

- [x] `pytest` passes: 156 total (7 new — lesson list, text rendering, popups, translations toggle, complete/cancel, bulk rating, jump-to-end).
- [x] Topic/lesson list (§8.1): topic dropdown, lessons in order with status + "last reviewed / never reviewed" + paragraph counts; double-click to review; "Finish saving" resumes incomplete lessons (M7 `FinalizeWorker`, background thread).
- [x] Lesson review text (§8.2–8.4): every CJK token is a clickable anchor; **static first-occurrence highlighting** of new words (D-1); word popups show pinyin/definition/list status with add-to-new/basic and basic→new actions committed immediately (§8.3, §5.3); per-sentence [译] translation toggles; percent-encoding-safe anchor handling.
- [x] Audio bar (§8.5): QMediaPlayer (FFmpeg backend confirmed working on this laptop) — play/pause, restart, 0.5×–2× speed, ±15s, "jump to end" → word review; graceful degradation if audio is missing.
- [x] Word review (§8.6): this lesson's learned words with 4-way ratings (standard default), multi-select + select-all + bulk apply.
- [x] Completion (§8.7): writes review events then applies SRS ratings, sets `last_reviewed_at`, offers next-lesson; **cancel writes nothing** (word-list actions taken during review remain, as specified).
- [x] Main-menu "Review a lesson" opens the topic/lesson list.

## M9 — Sync

- [x] `pytest` passes: 165 total (9 new — export, verification, incremental events, results import, most-recent-wins, corrupt rejection).
- [x] `services/sync.py`: **content bundle** (desktop → Android) — `sync-v1.zip` with `manifest.json` (schema version, counts, **SHA-256 of every file**), `content.json` (topics, lessons, sentences with segmentation, words with SRS state, lesson_words, hsk_words), `audio/lesson_<id>.mp3`, and `events.jsonl` (review events **since the last export**).
- [x] `verify_bundle`: re-verifies every checksum; rejects tampered files, missing manifests, bad zips, wrong schema versions, and wrong bundle types.
- [x] **Results import** (Android → desktop): verify **before** anything is applied → automatic DB backup (`backups/pre-import-<ts>.db`) → insert `device='android'` events → apply SRS ratings with the **most-recent-wins** conflict rule (§10) → update `last_reviewed_at` → apply word actions (add_new / add_basic / basic_to_new).
- [x] `write_results_bundle`: reference implementation of the results-bundle format (spec for the Android app).
- [x] Sync page UI (main menu "Sync with Android"): export with destination picker + summary, import with verification summary; both run in background workers with per-thread DB connections.
- [ ] Real round-trip with the Android app — by definition deferred to the Android implementation (roadmap step 6).

## M10 — Deployment

- [ ] (pending)
