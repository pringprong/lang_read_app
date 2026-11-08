# Lesson-Frequency-Based SRS Update — Plan

Date: 2026-11-08
Status: FINAL — clarification answers (§9) incorporated; ready to implement.

## 1. Goal

Replace the day-based spaced repetition system with a **lesson-frequency-based** one, so that
SRS behaves correctly when many lessons are created on the same day:

- Every generated paragraph automatically includes **a few words from the Learned list**,
  selected by a weighted probability combining:
  1. **Recency of first learning** — words learned only a few lessons ago are more likely to
     reappear; probability decays as the word becomes routine (e.g. over ~5 lessons).
  2. **Recency of last actual appearance** — the heart of spaced repetition: words that have
     *not* actually appeared in a lesson for a long time (in lesson counts) become more likely.
  3. **Difficulty rating** — the user's difficult/easy ratings (already collected during
     lesson review) bias selection. This is the **least important** factor, and it is simply
     absent (neutral) when the relevant lessons have not been reviewed yet.
- The system must track **which learned words actually appear in which paragraph of which
  lesson** (the LLM only takes suggestions), and use *actual appearances* — not suggestions —
  as the SRS exposure signal.
- The system stays **soft**: it just guarantees learned words keep reappearing across
  lessons regardless of creation date. No strict "due" enforcement.

Unchanged (already working well): 5 new words per lesson; random Basic-word samples per
paragraph; the paragraph generation pipeline; the review-time rating flow (difficult /
easy / standard / unchanged).

## 2. Current state (what changes and what stays)

| Component | Today | After this change |
|---|---|---|
| `services/srs.py` | SM-2 day engine: `interval_days`, `due_at`, ease; `promote`, `apply_exposure`, `apply_rating` | Rating math (ease/reps/lapses) **kept**; day-based intervals/`due_at` **removed entirely** (Q4); new lesson-frequency weight/selection engine added |
| `db/repositories/words.py` | `due_learned_words()` (due_at ordering) drives review-word suggestions | `due_learned_words()` removed; lesson-frequency candidate data instead |
| `services/cadence.py` | Review words = fixed wizard list, rotated by cursor, max 2/paragraph | Review words per paragraph chosen by the new **weighted selector**; first-use/repeat logic untouched |
| `services/generation.py` | Prompt gets `review_words` + 20 Basic words; `used_words` = requested ∩ tokens (already detects actual usage) | Selector picks per-paragraph learned words; also detect **all** learned words appearing (suggested or spontaneous) per paragraph; record them on the draft |
| `services/lesson_saver.py` | `_apply_exposure` grows day intervals for wizard-*selected* review words (whether or not they actually appear) | New **appearance recording** step: per-paragraph actual appearances saved, `last_seen_lesson_id` updated; day-interval exposure removed |
| `ui/lesson_create/word_select.py` | Review words: checkboxes of "due" learned words | Checkbox group removed (Q1); automatic per-paragraph selection; UI shows an informational preview |
| `ui/settings/srs_page.py` | Day-based SM-2 knobs | New lesson-frequency knobs; day-based knobs removed (Q4) |
| Schema | v3: SRS day fields on `words`; `lesson_words(role new/review)`; no appearance history | v4: `word_appearances` table + `words.first_learned_lesson_id` / `words.last_seen_lesson_id`; day columns dropped (no backfill needed — DB has 0 lessons) |

## 3. Core design: the lesson-frequency engine

### 3.1 Lesson ordinal ("lessons ago")

Every lesson gets its position in the **global lesson sequence** — simply its `lessons.id`
(auto-increment across all topics). "Lessons ago" for a word is:

```
age      = current_lesson_no − first_learned_lesson_id   (lessons since first learned)
gap      = current_lesson_no − last_seen_lesson_id        (lessons since last appearance)
```

- `current_lesson_no` = `MAX(lessons.id)` normally; while *generating* a not-yet-saved lesson
  it is `MAX(lessons.id) + 1`.
- Deleting the last lesson of a topic is already only allowed for the most recent lesson, and
  that delete demotes its new words back to the New list, so ids stay a valid sequence
  (SQLite rowid reuse only affects the deleted max id, which has no surviving references).
- Note: "which day a lesson was created" is *irrelevant* to this engine — only lesson order
  matters (this is the point of the change). See Q3 for global-vs-per-topic counting.

### 3.2 Per-word selection weight (pure function)

For each Learned word, compute three normalized components in `[0, 1]`, then a weighted sum:

1. **Novelty** (factor 1 — recency of first learning; decays to routine):
   `N = max(0, 1 − age / novelty_window_lessons)` with `novelty_window_lessons = 5` by
   default (per the user's example: learned within the last ~5 lessons → boost).
   Words first learned in the *current* lesson (the 5 new words) are not eligible at all —
   they already get the cadence repeat mechanism.
2. **Staleness** (factor 2 — the heart of the system):
   `S = min(1, gap / staleness_target_lessons)` with `staleness_target_lessons = 8` by
   default. A word that has not actually appeared for the target number of lessons is fully
   "stale" and always gets the maximum boost, guaranteeing every learned word eventually
   returns.
3. **Difficulty** (factor 3 — least important, from review ratings):
   `D = (ease_max − ease) / (ease_max − ease_min)` mapped to `[0,1]`; harder words (low
   ease) score higher. When the word has never been rated (`reps == 0` or
   `last_rated_at IS NULL`) → `D = 0.5` (neutral — the same constant for every unrated word,
   so it neither boosts nor suppresses anything; when many same-day lessons are unreviewed
   this factor simply contributes nothing to the *ranking*).

```
weight = w_novelty · N + w_staleness · S + w_difficulty · D
defaults:  w_novelty = 0.30,  w_staleness = 0.50,  w_difficulty = 0.20
```

Staleness gets the largest weight (it is the stated heart of the system); difficulty the
smallest (stated least important). All knobs are user-editable (see §5.4).

### 3.3 Per-paragraph selection

- For each paragraph, pick `learned_words_per_paragraph` (default **2**) distinct learned
  words by **weighted random sampling without replacement** (Efraimidis–Spirakis weighted
  sampling, or repeated weighted draws after removing the chosen word).
- **In-lesson cooldown:** a word that has already actually appeared in the current lesson is
  excluded from further suggestions in that lesson. This spreads different learned words
  across the paragraphs of one lesson instead of hammering the same high-scoring word in
  every paragraph.
- If the Learned list is small, fewer (or zero) words are picked — never an error.
- A `random.Random` instance is injected for deterministic tests.

### 3.4 Exposure = actual appearance

- The draft already computes `used_words` (requested ∩ segmented tokens) per paragraph. We
  extend paragraph post-processing to intersect tokens with the **entire Learned list**, so
  spontaneous (unsuggested) learned-word usage is also detected.
- These actual appearances are stored on the draft and written to the database at save time
  (§5.2). Suggested-but-unused words do **not** count as exposure; only real appearances move
  `last_seen_lesson_id`.

### 3.5 Ratings

The existing rating flow (review page → `SrsService.rate_word` → `review_events` log) is
kept unchanged, but the rating math is simplified now that day intervals are removed
(Q4 answer — the database holds no significant SRS data):

- `easy` → ease + `ease_delta_easy`; `difficult` → ease + `ease_delta_difficult` and
  lapses + 1 (ease clamped to `[ease_min, ease_max]`); `standard` → reps + 1 only;
  `unchanged` → no change at all. `promote` initializes ease to `initial_ease`.
- `ease` feeds the difficulty factor `D` above; `reps`/`lapses` remain for diagnostics
  and sync.
- `SrsState` loses `interval_days` and `due_at`; the `words` table loses those columns
  (schema v4); `apply_exposure` and all interval math are deleted outright.

## 4. Data model (schema v4)

### 4.1 New table — actual appearance history

```sql
CREATE TABLE word_appearances (
    word_id    INTEGER NOT NULL REFERENCES words(id)    ON DELETE CASCADE,
    lesson_id  INTEGER NOT NULL REFERENCES lessons(id)  ON DELETE CASCADE,
    para_index INTEGER NOT NULL,
    PRIMARY KEY (word_id, lesson_id, para_index)
);
CREATE INDEX idx_word_appearances_word ON word_appearances(word_id);
```

One row per (learned word, lesson, paragraph) in which the word **actually appears** —
including the paragraph where a word was first introduced. This is the ground truth the SRS
reads; deletions cascade with the lesson.

### 4.2 New columns on `words`

```sql
first_learned_lesson_id INTEGER REFERENCES lessons(id),  -- lesson that introduced it
last_seen_lesson_id     INTEGER REFERENCES lessons(id)   -- last lesson it actually appeared in
```

Both set to the introducing lesson's id at promotion; `last_seen_lesson_id` updated whenever
an appearance is recorded. These make the weight computation a single lookup per word (no
scan of `word_appearances` needed for selection).

### 4.3 Migration (connection.py `migrate()`, v4)

- `ALTER TABLE words ADD COLUMN ...` for both new columns (kept in `schema.sql` too, per the
  existing v2/v3 convention).
- Create `word_appearances`.
- **Drop the day-based SRS columns** `words.interval_days` and `words.due_at`
  (`ALTER TABLE ... DROP COLUMN`; SQLite ≥ 3.35 — the runtime's bundled version will be
  checked, with a create-new-table-and-copy fallback if it is older).
- Per the Q4 answer the current database has **0 lessons and 0 learned words**, so no
  backfill is needed. The migration still handles the general case defensively (in case of
  test databases or future reuse): if lessons exist, the two new word columns are derived
  from `lesson_words` (role `new` → both = that lesson; role `review` → `last_seen`) and
  appearances are rebuilt from sentence segmentations; for the current database this is a
  trivial no-op.

### 4.4 Sync (Q5 answer: minimal Android changes)

The sync bundle is the zip the desktop app exports so the Android app can display lessons
and send back ratings; `services/sync.py` exports `words` including SRS fields. Changes:

- The words export drops `interval_days` / `due_at` (the columns no longer exist) and adds
  `first_learned_lesson_id` / `last_seen_lesson_id`.
- `word_appearances` is **not** exported — the Android app never computes or displays it.
- The Android app only *receives* SRS values and never computes them, so the two new
  fields are additive and ignorable. The removed old fields are the only compatibility
  risk (the Android import maps `content.json` keys to its local schema — to be verified
  during implementation; worst case its importer tolerates absent keys). No Android-side
  feature changes are part of this update.

## 5. Pipeline changes

### 5.1 Generation (`services/generation.py` + `services/cadence.py`)

1. `generate_lesson` builds a **LearnedWordSelector** (new pure class, living next to the
   SRS engine) from all Learned words + `current_lesson_no` + the SRS params.
2. Per paragraph: the selector picks up to K learned words (§3.3) → these become the
   paragraph's `{review_words}` in the prompt templates (templates unchanged — the
   placeholder already exists and the prompt already says "use these review words if they
   fit naturally", which matches the "LLM takes suggestions" requirement).
3. After the LLM reply: intersect the paragraph's segmented tokens with the Learned list →
   `paragraph.learned_used` (superset of what was suggested). Feed back to the selector
   (in-lesson cooldown) and, as today, to `planner.record_usage`.
4. `GeneratedParagraph` gains `learned_used: list[str]`; `LessonDraft` keeps `review_words`
   as the (now informational) list of suggested learned words for the whole lesson.
5. `CadencePlanner`: remove the cursor-rotation `_next_review`; `ParagraphPlan.review_words`
   is filled in by the generation service per paragraph. First-use/repeat/final-paragraph
   rules untouched.
6. `suggest_lesson_words()` (wizard info): review suggestions now come from the selector's
   top-weighted words (for display only — selection itself is automatic).

### 5.2 Save pipeline (`services/lesson_saver.py`)

In `save_lesson` / `finalize_lesson`:

- **New step — record appearances** (idempotent, `INSERT OR IGNORE`): for each paragraph of
  the final (possibly hand-edited) draft, intersect the paragraph's final segmentation with
  the Learned list → `word_appearances` rows; for each such word update
  `last_seen_lesson_id` = this lesson (with a `MAX()` guard for resume-idempotency). This
  runs **after** the user's step-3 hand edits, so the saved truth matches the saved text (a
  word the user deletes while hand-editing is correctly *not* an exposure, and a word the
  user types in *is* one).
- `lesson_words(role='review')` rows are written from **actual appearances** (instead of the
  wizard's checked list), so the review page's rating list (which reads `lesson_words`)
  automatically reflects what the user really just read — including spontaneous appearances.
- **Promotion** (`_promote_new_words`): also set `first_learned_lesson_id` and
  `last_seen_lesson_id` = this lesson id, and write the appearance row for the paragraph
  where the word was first used.
- **`_apply_exposure` removed** (replaced by the appearance step; no more day-interval
  growth). No review event is written for appearances, as today.

### 5.3 Wizard UI (`ui/lesson_create/word_select.py`)

The "Review words (previously learned, due for review)" checkbox group is replaced with a
read-only preview: e.g. "SRS will automatically weave ~2 learned words into each paragraph"
plus a non-interactive list of the currently highest-weighted words (novel / stale / hard),
so the user has visibility without manual selection. (Q1 answer: the checkbox group is
removed; selection is fully automatic.)

### 5.4 Settings (`ui/settings/srs_page.py` + `SrsParams`)

`SrsParams` is rebuilt (stored under the same `srs.params` settings key; unknown old keys are
already ignored on load). Final parameter set:

Lesson-frequency (new):
- `learned_words_per_paragraph` (default 2) — Q2 answer, user-configurable
- `novelty_window_lessons` (default 5)
- `staleness_target_lessons` (default 8)
- `weight_novelty` / `weight_staleness` / `weight_difficulty` (0.30 / 0.50 / 0.20)
- `same_lesson_cooldown_paragraphs` (default 0 = whole lesson)

Rating math (kept from the old engine):
- `initial_ease`, `ease_delta_easy`, `ease_delta_difficult`, `ease_min`, `ease_max`

Removed entirely (day-based, per the Q4 answer): `initial_interval_days`,
`exposure_multiplier`, `easy_bonus`, `relearn_interval_days`, `min_interval_days`,
`max_interval_days`.

The settings page renders `fields(SrsParams)` automatically, so it follows the dataclass;
only the `PARAM_HELP` tooltips need updating.

## 6. Files to touch

```
src/langread/db/schema.sql                      v4: word_appearances + 2 word columns
src/langread/db/connection.py                   v4 migration + backfill
src/langread/models/entities.py                 Word: first/last lesson ids
src/langread/db/repositories/words.py           new columns in row mapping; set/lookup
                                                 helpers; lesson-frequency candidates
src/langread/db/repositories/lessons.py         appearance insert/list helpers
src/langread/services/srs.py                    new LessonSrsParams + weight/selector
                                                 (pure), promote sets lesson ids, exposure
                                                 removed
src/langread/services/cadence.py                review words supplied per paragraph
src/langread/services/generation.py             selector wiring, learned_used detection
src/langread/services/lesson_saver.py           appearance recording step, role='review'
                                                 from actual appearances, promotion update
src/langread/ui/lesson_create/word_select.py    informational preview (checkbox group
                                                 removed, Q1)
src/langread/ui/settings/srs_page.py            new knobs, day knobs removed (+ PARAM_HELP)
src/langread/services/sync.py                   word field set update only (Q5: minimal)
src/langread/resources/prompts/default_templates.json   unchanged (placeholders reused)
tests/unit/test_srs_engine.py + new test_lesson_srs.py  weight & selector tests
                                                 (engine tests rewritten: ease-only rating)
tests/unit/test_cadence.py                      per-paragraph review words
tests/integration/test_generation.py            learned-word weaving + usage feedback
tests/integration/test_lesson_saver.py          appearance recording, exposure replacement
tests/integration/test_sync.py                  export includes new fields
tests/integration/test_lesson_wizard_ui.py      step-1 UI change
```

## 7. Test plan

- **Unit — weight function:** novelty decays linearly to 0 at the window edge; staleness
  saturates at the target; difficulty neutral (0.5) when unrated; hard word (low ease) scores
  above easy word; all components clamped to `[0, 1]`.
- **Unit — selector:** seeded RNG determinism; no word picked twice in one lesson
  (cooldown); words learned in the current lesson excluded; empty/small Learned list →
  fewer/zero picks; over many seeded trials, stale words are picked far more often than
  freshly-used ones (statistical smoke with loose thresholds).
- **Integration — generation:** fake LLM (existing test pattern) includes the suggested
  learned words; `learned_used` also contains a spontaneous learned word the LLM added on
  its own; later paragraphs don't re-suggest words already used.
- **Integration — save:** appearances written per paragraph; `last_seen_lesson_id` advanced
  only for actually-appearing words; `lesson_words(role='review')` matches actual
  appearances; promotion sets both lesson ids; the step is idempotent under
  `finalize_lesson` resume; hand-edited text (word added/removed in step 3) is reflected.
- **Integration — migration:** a v3 database upgrades cleanly: `word_appearances` and the
  two new word columns exist, the day columns are gone, and word/topic data is intact.
- **Regression:** review rating flow (ease-only math), wizard save flow, sync
  export/import round-trip.

## 8. Out of scope / assumptions

- The 5-new-words-per-lesson rule, Basic-word sampling, TTS, translations, and the rating UI
  are untouched.
- Deleting a lesson still cascades its appearances; the only-last-lesson deletion rule
  already protects sequence integrity.
- The engine is intentionally soft: no "overdue" queues and no guarantee that a specific word
  appears within N lessons — only weighted probability, with a staleness term that eventually
  dominates for neglected words so they all come back.
- Performance is a non-issue at expected scale (hundreds of learned words), but the
  candidate set is loaded once per generation run, not per paragraph.

## 9. Clarification questions — answers (2026-11-08)

**Q1 — Wizard review-word checkboxes → REMOVE.** The step-1 checkbox group is deleted;
learned words are woven into paragraphs fully automatically. The page shows a read-only
informational preview of the currently highest-weighted learned words.

**Q2 — Words per paragraph → 2, configurable.** Default of 2 learned words per paragraph,
exposed as the user-configurable `learned_words_per_paragraph` setting.

**Q3 — Lesson counting → global, creation-based.** Lessons are counted globally across all
topics using `lessons.id`, and the SRS clock ticks on lesson *creation*, including for
lessons that have never been reviewed.

**Q4 — Day-based SRS fields → REMOVE.** The database currently holds 123 new words,
0 learned words, >1000 basic words, 1 topic, and 0 lessons (all lessons deleted), so nothing
of value is lost. Removed outright: the `words.interval_days` / `words.due_at` columns, the
day-based `SrsParams` knobs and settings fields, `apply_exposure`, and
`due_learned_words()`. The rating math keeps only ease/reps/lapses (§3.5).

**Q5 — Android sync → minimal changes.** Only the desktop export's word field set changes:
drop the two day fields, add the two lesson-id fields. `word_appearances` is not exported.
No Android-side feature changes.

All questions are resolved — the plan is ready to implement.




