# Desktop App — Detailed Implementation Plan

- **Date:** 2026-11-01
- **Based on:** `20261101_language_app_reqs.md` v1.1 (all section references "§n" point to that document)
- **Status:** Plan; implementation begins after approval

---

## 1. Technology Stack (decisions)

| Layer | Choice | Rationale |
|---|---|---|
| Language | **Python 3.11+** | D-8: "Python as much as possible"; runs identically on Windows and Linux. |
| GUI framework | **PySide6 (Qt 6, official LGPL bindings)** | Native widgets on both platforms; `QTextBrowser` with anchors gives per-word clickable Chinese text; `QMediaPlayer` gives MP3 playback with speed (`setPlaybackRate`) and seeking (`setPosition`) for the ±15s jumps (§8.5); mature, well-documented. |
| Database | **SQLite** (stdlib `sqlite3`) | Single-file local DB, WAL mode, trivially backupable (D-3 requirement); same engine available on Android (plan phase 3) so the sync bundle is easy to reconcile. |
| Chinese segmentation | **jieba** | D-5: local segmentation primary; custom dictionary loaded from the app's word lists so app words always segment correctly. |
| Pinyin | **pypinyin** | Offline pinyin generation as a cross-check for the translation model's pinyin output. |
| LLM/TTS HTTP | **`openai` Python client** | Works with any OpenAI-compatible endpoint via `base_url` (LM Studio, Kokoro's OpenAI-compatible server, Alibaba Cloud) — matches D-4 exactly. |
| Audio playback | **Qt Multimedia (`QMediaPlayer`)** | Built into PySide6; MP3 + rate + seeking. Fallback if a Linux machine lacks the GStreamer/FFmpeg backend: `python-vlc` behind a thin player interface. |
| Packaging | **PyInstaller** (one-dir) | Same `main.py` produces a Windows folder-exe and a Linux binary; HSK data + prompt templates bundled as package resources. |
| Env/deps management | **`uv`** (or plain `venv` + `pip`) with `pyproject.toml` | Reproducible on both OSes. |
| Tests | **pytest** | Unit + integration (with a fake OpenAI-compatible server). |

**Cross-platform notes:** all paths built with `pathlib`; app data lives in a per-OS user data dir (`%LOCALAPPDATA%/LangReadApp` on Windows, `~/.local/share/LangReadApp` on Linux) with a `LANGREAD_DATA_DIR` env override for tests.

## 2. Architecture

Layered architecture; UI never touches SQL, services never touch Qt.

```
lang_read_app/
├── pyproject.toml
├── README.md
├── src/langread/
│   ├── main.py                  # entry point, QApplication bootstrap
│   ├── app_config.py            # paths, data dir, resource loading
│   ├── db/
│   │   ├── schema.sql           # DDL (migrations applied in order)
│   │   ├── connection.py        # sqlite3 conn, WAL, context manager
│   │   └── repositories/        # topics.py, lessons.py, sentences.py,
│   │                            # words.py, hsk.py, settings.py,
│   │                            # reviews.py, templates.py
│   ├── models/                  # dataclasses: Topic, Lesson, Sentence,
│   │                            # Word, HskWord, ReviewEvent, …
│   ├── services/
│   │   ├── srs.py               # SM-2 variant engine (§11 / D-2)
│   │   ├── segmentation.py      # jieba + custom dict + LLM fallback (D-5)
│   │   ├── generation.py        # lesson text generation pipeline (§7)
│   │   ├── cadence.py           # word-usage tracking & next-prompt word pick (§7.6)
│   │   ├── llm_client.py        # OpenAI-compatible chat client (config-driven)
│   │   ├── translation.py       # word defs/pinyin + sentence translation (§9.2)
│   │   ├── tts.py               # lesson MP3 generation (Kokoro) (§9.3)
│   │   ├── lesson_saver.py      # atomic save pipeline (§7.9)
│   │   ├── hsk.py               # bundled HSK dataset loading/import
│   │   └── sync.py              # bundle export/import + verify + backup (§10 / D-3)
│   ├── resources/
│   │   ├── hsk/hsk.csv          # bundled HSK 1–6 data (D-7)
│   │   └── prompts/default_templates.yaml  # seed prompt templates
│   └── ui/
│       ├── main_menu.py         # §12.1
│       ├── topic_lesson_list.py # §8.1
│       ├── review/
│       │   ├── lesson_review.py # §8.2–8.7 (text, popups, word review)
│       │   └── audio_bar.py     # play/pause/restart/speed/±15s/end
│       ├── lesson_create/
│       │   ├── wizard.py        # §7 step flow
│       │   ├── word_select.py   # §7.2
│       │   ├── generate_view.py # §7.3–7.7 progress + per-unit retry
│       │   └── final_edit.py    # §7.8 text + segmentation editing
│       ├── words/
│       │   ├── list_manager.py  # New/Learned/Basic tabs + moves
│       │   ├── hsk_browser.py   # §5.5
│       │   └── paste_import.py  # §5.1
│       ├── settings/
│       │   ├── models_page.py   # URLs/keys/models (§9)
│       │   ├── templates_page.py# prompt template editor (§4.5)
│       │   └── srs_page.py      # SRS parameter editor (§11)
│       └── sync_page.py         # §10 export/import + verify UI
└── tests/
    ├── unit/                    # srs, cadence, segmentation, repos
    ├── fakes/                   # fake OpenAI-compatible server, fake TTS
    └── integration/             # generation pipeline, save pipeline, sync
```

**Threading rule:** all LLM/TTS network calls run in `QThread` workers (or `concurrent.futures` + Qt signals) so the UI stays responsive; workers report progress for the multi-step pipelines.

## 3. Database Schema (SQLite)

```
topics(id INTEGER PK, name TEXT UNIQUE, order_index INT, created_at TEXT)

lessons(id PK, topic_id FK→topics, order_index INT, title TEXT,
        status TEXT CHECK(status IN ('draft','complete','incomplete')),
        audio_path TEXT NULL, created_at TEXT, last_reviewed_at TEXT NULL)

sentences(id PK, lesson_id FK→lessons, para_index INT, sent_index INT,
          text TEXT, segmentation TEXT /* JSON array of word tokens */,
          translation TEXT NULL)

words(id PK, text TEXT UNIQUE /* simplified, no spaces */,
      pinyin TEXT NULL, definition TEXT NULL,
      list_state TEXT CHECK(list_state IN ('new','learned','basic')),
      hsk_word_id INT NULL FK→hsk_words,
      source TEXT /* 'paste','manual','lesson','basic','hsk' */,
      added_at TEXT,
      /* SRS fields, valid when list_state='learned' (D-2): */
      ease REAL DEFAULT 2.5, interval_days REAL NULL,
      due_at TEXT NULL, reps INT DEFAULT 0, lapses INT DEFAULT 0,
      last_rated_at TEXT NULL)

word_topics(word_id FK→words, topic_id FK→topics, PRIMARY KEY(word_id, topic_id))

lesson_words(lesson_id FK→lessons, word_id FK→words,
             role TEXT CHECK(role IN ('new','review')),
             PRIMARY KEY(lesson_id, word_id))

hsk_words(id PK, text TEXT, pinyin TEXT, definition TEXT, level INT,  /* 1..6 */
          app_state TEXT CHECK(app_state IN ('unused','new','basic','learned')),
          UNIQUE(text, level))
          -- reference data (§4.4): never deleted, only app_state is updated

review_events(id PK, lesson_id FK, word_id FK NULL, rating TEXT NULL
              CHECK(rating IN ('difficult','easy','standard','unchanged')),
              reviewed_at TEXT, device TEXT CHECK(device IN ('desktop','android')))
              -- append-only log; drives Android→desktop sync reconciliation (§10)

settings(key TEXT PK, value TEXT /* JSON */)
          -- model endpoints/keys, SRS params, generation unit, sync metadata

prompt_templates(name TEXT PK, template TEXT, updated_at TEXT)
```

Notes:
- Word list membership is the single `words.list_state` column (§4.4); moving a word between lists is one UPDATE plus HSK `app_state` sync.
- Lesson `status='incomplete'` marks a save pipeline interrupted mid-way (§7.9 atomicity); the app shows a "finish saving" resume action.
- Segmentation is stored per sentence as a JSON token array (D-5), hand-editable in the final-edit step.
- `review_events` is the source for SRS updates *and* the Android sync payload; SRS fields on `words` are a materialized current state.

## 4. SRS Engine (SM-2 variant, D-2)

State per learned word: `ease` (default 2.5, clamped [1.3, 3.0]), `interval_days`, `due_at`, `reps`, `lapses`.

All knobs live in `settings` and are editable in the SRS settings page (§12.1 item 7):

| Parameter | Default | Meaning |
|---|---|---|
| `initial_interval_days` | 1 | interval on promotion to Learned |
| `exposure_multiplier` | 1.0 | interval growth when a word is merely *used in a newly created lesson* (§7.9.4) |
| `easy_bonus` | 1.3 | extra multiplier for "easy" rating |
| `ease_delta_easy` | +0.15 | ease change on "easy" |
| `ease_delta_difficult` | −0.20 | ease change on "difficult" |
| `relearn_interval_days` | 0.5 | interval after "difficult" |
| `min_interval_days` / `max_interval_days` | 1 / 365 | interval clamps |

Update rules:
- **Promotion (new→learned):** `interval=initial`, `due_at=now+initial`, `ease=2.5`, `reps=1`.
- **Exposure (used in a new lesson):** `interval = clamp(interval × ease × exposure_multiplier)`, `due_at` recomputed. (Gentle growth, per §1.2 "not strict".)
- **Review ratings (§8.6):**
  - `standard` → `interval = clamp(interval × ease)`, `reps+1`.
  - `easy` → `interval = clamp(interval × ease × easy_bonus)`, `ease += ease_delta_easy`, `reps+1`.
  - `difficult` → `interval = relearn_interval`, `ease += ease_delta_difficult` (clamped), `lapses+1`.
  - `unchanged` → no change.
- **Due-word suggestions (§7.2):** `ORDER BY due_at ASC`, learned words of the same topic first, then any due word.
- Every rating writes a `review_events` row *before* applying the update, and lesson review completion writes the lesson's `last_reviewed_at` only on "mark complete" (§8.7); cancel writes nothing.

Pure-function core (`apply_rating(state, rating, params, now) → state`) so the engine is fully unit-testable.

## 5. Model Integration Layer

### 5.1 Configuration (settings keys)
- `gen.base_url`, `gen.api_key` (optional), `gen.model`, `gen.temperature`
- `trans.base_url`, `trans.api_key`, `trans.model`
- `tts.base_url`, `tts.api_key`, `tts.model` (Kokoro), `tts.voice` (Chinese voice), `tts.speed`
- All edited on the Models settings page with a **"Test connection"** button per service.

### 5.2 LLM client
- Thin wrapper over the `openai` package client with `base_url`/`api_key`/`model` injected from settings.
- Supports chat-completions with plain text response; expects the model to return **JSON when the prompt asks for JSON** (parsing is defensive: extract the first JSON block, retry once with a "return only JSON" fix-up prompt on parse failure).

### 5.3 Prompt templates (stored in `prompt_templates`, seeded from resources, editable in-app §4.5)
| Template | Used for |
|---|---|
| `segment_text` | LLM fallback: split pasted/generated text into word tokens (JSON array) (§5.1, D-5) |
| `parse_pasted_text` | Full parse of user-pasted text into unique words (§5.1) |
| `generate_paragraph` | One paragraph of a lesson (§7.4, D-12 default) |
| `generate_sentence` | One sentence of a lesson (fallback unit) |
| `generate_final_paragraph` | The constrained last paragraph (§7.7) |
| `translate_word` | definition + pinyin for one word (JSON) (§9.2) |
| `translate_sentence` | whole-sentence English translation (§9.2) |

Placeholders in `{curly_braces}` (e.g. `{new_word}`, `{repeat_words}`, `{review_words}`, `{basic_sample}`, `{topic_name}`, `{paragraph_index}`, `{total_paragraphs}`) are filled by the generation service; unknown placeholders raise a visible template-validation error, and the editor page highlights available placeholders.

### 5.4 TTS service
- Posts the final lesson text (paragraphs joined with pauses) to the Kokoro OpenAI-compatible `/audio/speech` endpoint; writes `audio/lesson_<id>.mp3`; verifies a non-empty MP3 file (header check) and duration sanity.

## 6. Segmentation Service (D-5)

1. Load **jieba** with a custom dictionary built from all `words` + `hsk_words` rows (so any word the app knows is segmented atomically; dictionary reloaded after word-list changes).
2. Segment text → token list; strip punctuation into separate tokens for rendering.
3. If a token is not in any app list *and* jieba's confidence is low (unknown multi-char token), optionally send the surrounding sentence to the LLM `segment_text` fallback.
4. Return tokens + per-token `list_state`/`word_id` resolution (used by review-time popups §8.3 and usage tracking §7.6).
5. The final-edit screen lets the user **merge/split tokens by hand** (D-6); manual edits are saved into `sentences.segmentation`.

## 7. Lesson Generation Pipeline (§7)

### 7.1 Cadence algorithm (`services/cadence.py`)
Inputs: `N` paragraphs (5–10, user-confirmed), new words `W` (5–10), review words `R`, basic-word sample.

- **First-use assignment:** the new words are introduced one per paragraph across paragraphs `1 … |W|` (since |W| ≤ 10 ≤ N−1, none falls in the final paragraph — §6.4). If |W| ≥ N, user must add paragraphs or drop words.
- **Per-paragraph word list** for the prompt:
  - exactly one first-use new word (paragraphs 1..|W|);
  - repeat words = previously introduced new words with the **lowest usage counts** (ensures each appears "multiple times", §6.3);
  - review words due soonest (same-topic first);
  - all words already used in ≥1 earlier paragraph of this lesson are listed as "must not be the only vocabulary" context.
- **Final paragraph (§7.7):** prompt requires *all* of `W`, no first-use words.
- **After each unit is generated:** segment it, count actual usage of each requested word, update the tally, and compute the next paragraph's list. If the first-use word is missing from a generated paragraph → automatic retry (same prompt + "you MUST use X"), max 2 retries, then mark the paragraph for the user's attention in the wizard.

### 7.2 Wizard flow (`ui/lesson_create/wizard.py`)
1. **Word selection** (§7.2): two lists — suggested new words (D-11: oldest-added, topic-first) and suggested review words (SRS due, topic-first); user can add/remove/swap; validation 5–10 new words.
2. **Paragraph count** (5–10, default 8, must be > |W|).
3. **Generation** (§7.3–7.7): background worker generates paragraph by paragraph; progress view shows each finished paragraph with its used-words tally, per-paragraph regenerate button, pause/cancel. Word-list change mid-way regenerates the *entire* lesson (§7.8).
4. **Final review / hand edit** (§7.8, D-6): plain-text editor per paragraph + segmentation editor (merge/split tokens); re-segmentation runs after text edits; the app warns if any required word is missing after edits.
5. **Approve & save** → hands off to `lesson_saver`.

### 7.3 Save pipeline (`services/lesson_saver.py`, §7.9)
Executed in a background worker with per-step progress, resumable after interruption (lesson stays `status='incomplete'`):
1. TTS: one MP3 for the whole lesson (D-1).
2. Translations: whole-sentence translation per sentence (batched, sequential).
3. Word promotion: for each new word — translation-model definition + pinyin (cross-checked with pypinyin, LLM value preferred), move `list_state new→learned`, init SRS, record `lesson_words(role='new')`, update `word_topics`, HSK `app_state='learned'`.
4. SRS exposure updates for review words; record `lesson_words(role='review')`.
5. Insert sentences (text, segmentation, translation).
6. Insert lesson (topic's next `order_index`), `status='complete'`.
All steps inside one SQLite transaction per step + idempotent resume by checking what already exists.

## 8. Lesson Review UI (§8)

- **Text rendering:** lesson text is rendered in a `QTextBrowser` using HTML: each word token is an anchor (`<a href="w:<word_id>">`), punctuation rendered plain, paragraphs spaced. First occurrence of each of the lesson's new words gets a highlight background class (static, D-1).
- **Word popup (§8.3):** clicking an anchor opens a small popup/panel: word, pinyin, definition, list status, and the actions — "Add to Basic list", "Add to New list" (if unlisted), "Move Basic→New" (if basic). Actions commit immediately (per §8.7 note).
- **Sentence translation (§8.4):** each sentence ends with a small toggle (▸) that reveals the stored translation below it.
- **Audio bar (§8.5, `ui/review/audio_bar.py`):** wraps `QMediaPlayer` — play/pause, restart, speed selector (0.5×–2.0×, via `setPlaybackRate`), −15s/+15s (via `setPosition`), "skip to end" button that jumps to the word-review stage. The player sits behind a small interface so `python-vlc` can be dropped in if a Linux box lacks the Qt multimedia backend.
- **Word review (§8.6):** after audio ends (or skip-to-end), a table of this lesson's Learned-list words, each with a 4-way choice (difficult/easy/standard/unchanged, default standard), multi-select + select-all + bulk-apply. "Mark review complete" writes `review_events` rows (device='desktop'), applies SRS updates, sets `last_reviewed_at`, then offers "next lesson" or "back to lesson list". **Cancel** writes nothing (§8.7).

## 9. Sync Design (§10 / D-3, desktop side)

**Bundle format** (a zip produced and consumed by the desktop app; the Android app produces/consumes the same format — finalized in the Android plan):

```
sync-v1.zip
├── manifest.json          # schema_version, created_at, counts, sha256 of every file
├── content.json           # topics, lessons, sentences, words (incl. SRS state),
│                          # lesson_words, hsk app_state
├── audio/lesson_<id>.mp3  # one file per lesson
└── events.jsonl           # desktop-side review_events since last export (optional)
```

- **Export (desktop → Android):** pick a destination (USB-connected device's visible folder or any local path); write the bundle; verify checksums of everything written.
- **Import (Android → desktop):** pick a results bundle; **verify manifest + all checksums before applying anything**; **auto-backup** the desktop DB (`backups/pre-sync-<timestamp>.db`) first; then apply: insert `device='android'` review_events, re-apply ratings by timestamp (most recent wins, §10), update `last_reviewed_at`, and apply word-list actions logged on Android.
- Corrupt or partial bundles are rejected with a clear error; nothing is applied. Import/export history is shown on the sync page.

## 10. HSK Dataset (D-7)

- **Sourcing step (first task of M5):** find a permissively-licensed public HSK 1–6 dataset (GitHub CSV/JSON — the widely-used old-standard HSK 2012 lists: 150/300/600/1200/2500/5000 words). Verify per-level counts, spot-check entries, commit the normalized CSV to `src/langread/resources/hsk/hsk.csv`.
- On first run (or via a settings action), the CSV is imported into `hsk_words` with `app_state='unused'`.
- HSK browser (§5.5): level tabs 1–6, in-list order; "unused only" filter; multi-select bulk "Add to New list" / "Add to Basic list"; each add updates `hsk_words.app_state` and links `words.hsk_word_id`.

## 11. Milestones

Each milestone ends with runnable, testable code (pytest green + manual smoke check).

| # | Milestone | Contents | Acceptance |
|---|---|---|---|
| M0 | Scaffolding | `pyproject.toml`, package layout, data-dir resolution, app boots an empty main-menu window on Linux | App runs |
| M1 | Data layer | `schema.sql`, migrations, repositories, model dataclasses | Unit tests for every repo pass |
| M2 | SRS engine | `services/srs.py` + parameter persistence | Full rating/exposure/promotion test matrix passes |
| M3 | Model layer | `llm_client`, TTS client, settings storage, models settings UI with test-connection, template storage/editor | Works against fake server; real LM Studio/Kokoro smoke test |
| M4 | Segmentation | jieba + custom dict + LLM fallback + segmentation editor | Unit tests incl. custom-dict priority; hand merge/split works |
| M5 | Word lists & HSK | list manager UI (New/Learned/Basic tabs, moves), paste-import, manual add, HSK dataset + browser with bulk actions | All §5 flows usable end-to-end |
| M6 | Lesson creation | wizard: word selection + suggestions, cadence, paragraph generation with retries, final edit, regenerate-all | Full §7 flow against fake + real LLM |
| M7 | Save pipeline | `lesson_saver` (TTS, translations, promotion, SRS, sentences, lesson insert) with resume | Interrupted save recovers; data consistent |
| M8 | Review UI | topic/lesson list with review history; review screen (text, popups, translations, audio bar, word review, complete/cancel) | Full §8 flow works |
| M9 | Sync | bundle export/import, verification, backups, Android-event application | Round-trip test with a hand-made Android bundle |
| M10 | Deployment | PyInstaller builds for Windows + Linux, run docs, end-to-end smoke test | Installed app works on both OSes; production use begins |

## 12. Testing Strategy

- **Unit:** SRS engine (pure functions), cadence planner, segmentation, repositories (temp DB per test), sync verification logic.
- **Integration:** a local **fake OpenAI-compatible server** (test fixture) returning canned text/JSON/MP3 bytes; drives the generation pipeline, save pipeline, and sync round-trips.
- **Manual smoke checklist** per milestone (kept in `docs/smoke_checklist.md`), including real LM Studio + Kokoro + Alibaba Cloud fallback runs.

## 13. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Qt multimedia backend missing on some Linux distros | Player behind an interface; `python-vlc` fallback; document required system packages. |
| Local 9B–12B models write poor paragraphs or ignore word constraints | Per-paragraph retry with hard constraints; D-12 switch to sentence unit; Alibaba Cloud fallback (D-4). |
| Kokoro Chinese voice quality | Voice configurable; the TTS endpoint is generic — any OpenAI-compatible TTS can replace it without code changes. |
| HSK dataset licensing/quality | Choose a permissively-licensed source, verify counts, commit CSV for git review. |
| USB transfer ergonomics (MTP quirks) | Sync works with any user-accessible folder; the app never talks to MTP directly. |
| Long lessons exceed TTS request limits | TTS called per paragraph and audio concatenated into the single lesson MP3 (D-1 preserved). |

## 14. Definition of Done (desktop; roadmap step 5)

- All §12.1 desktop main-menu functions work end-to-end with real models (Kokoro + LM Studio, Alibaba fallback tested).
- A lesson can be created, saved, reviewed, and re-reviewed; SRS values visibly drive subsequent lesson suggestions.
- Sync bundle round-trips correctly (verified with a simulated Android bundle).
- Packaged app runs on Windows and Linux from a clean install.




