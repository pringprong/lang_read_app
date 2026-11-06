# Dictionary Integration Plan — offline English word definitions (2026-11-06, v2)

> **v2 revision:** requirements clarified — definitions must be **in
> English** and the app is **simplified-Chinese only**. MengDict-DB-0.1 was
> assessed and **rejected** (§2.1); the zh-zh reader.dict files from v1 of
> this plan are **rejected** (§2.2); the recommended dictionary is now
> **CC-CEDICT** (§2.3). The integration architecture from v1 carries over
> with the parsing layer swapped.

## 1. Goal

Word definitions currently come from three unreliable sources: the bundled HSK
CSV (terse English glosses), the translation LLM (`translate_word` prompt), and
the HSK link fill-in. Many existing definitions are incorrect or incomplete.
This plan adds an **offline English dictionary lookup** that runs **before**
the LLM:

> dictionary hit → use it; dictionary miss → fall back to the translation
> model; model unavailable/failed → leave blank (pinyin still falls back to
> pypinyin).

Requirements pinned by the user:

- Definitions in **English**.
- **Simplified Chinese only** — headwords and all app data stay simplified.
- A one-time **refresh of all existing definitions** in the database, since
  most of them are wrong.

---

## 2. Dictionary assessment

### 2.1 MengDict-DB-0.1 — **not suitable** ❌

`dictionaries/MengDict-DB-0.1.tar.gz` was unpacked and inspected. It is a
2004-era project containing:

| Component | Content |
|---|---|
| `sql/*.sql` | MySQL `CREATE TABLE` schemas only — **zero data** (no INSERT statements in any file) |
| `sql/mengdict-schema.xml` | Table definitions (hanzi, cihui, pinyin, definitions, examples, radicals) |
| `import/*.php` | PHP scripts to load the data into MySQL |
| `import/Unihan.txt.bz2` | The **only actual data**: the Unicode Unihan database, version 3.2 (March 2002) |

Why it fails the app's needs:

1. **No word-level definitions.** The app looks up *words* (厨房, 学习,
   电脑 — the segmentation service produces multi-character tokens). The
   `cihui` ("vocabulary") tables that would hold word definitions are empty;
   only single characters have glosses, from Unihan `kDefinition`
   (19,401 entries, e.g. 厨 → "kitchen; closet; cupboard"). A word like
   厨房 would have to be faked from two character glosses — wrong and
   confusing.
2. **The data is 20+ years old** (Unicode 3.2, 2002) — missing modern
   characters, and glosses are often terse/obscure ("(corrupted form) to
   follow…").
3. **Not a usable database.** The SQL files are MySQL-only schema, the
   import scripts are PHP; the only parseable artifact is the raw Unihan
   TSV (character-level only, UPPERCASE tone-number pinyin like
   `CHU2 FANG2`).
4. **No word pinyin either** — kMandarin is per-character, one line per
   reading.

(Its one redeeming part — Unihan.txt — is public domain and already
superseded for this app by `pypinyin`, which provides character pinyin
offline.)

### 2.2 The five reader.dict zh-zh files — **not suitable** ❌

As analysed in v1 of this plan: all five are the same Chinese-Wiktionary
zh→zh dictionary in different containers (StarDict/dict.org/dictfmt/Kobo/
Mobi). Definitions are **in Chinese** and mostly **traditional script** —
both violate the clarified requirements. No further consideration.

### 2.3 Recommended dictionary: **CC-CEDICT** ✅

CC-CEDICT (the continuation of Denisowski's CEDICT, maintained via MDBG /
cc-cedict.org) is the standard open Chinese→English dictionary and matches
every requirement:

- **Simplified headwords** — every line carries both the traditional and
  the simplified form; the app indexes on the simplified form.
- **English definitions**, American English, sense-separated.
- **Pinyin per word** with tone numbers.
- **125,396 entries** (verified in the current download, revision of
  2026-10), actively maintained.
- **Format:** one plain-text UTF-8 line per entry, trivially parseable
  (no StarDict binary work needed — simpler than the v1 plan):

  ```
  皮實 皮实 [pi2 shi5] /(of things) durable/(of people) sturdy; tough/
  廚房 厨房 [chu2 fang2] /kitchen/CL:間|间[jian1]/
  ```

  Line grammar: `Traditional Simplified [pin1 yin1] /gloss; gloss/…/`;
  senses are separated by `/`, glosses within a sense by `;`; `u:` means
  ü; proper nouns have capitalised pinyin (`[Bei3 jing1]`); `CL:…` marks
  measure words; `Xxx[…]` references inside glosses point at other words.
- **License:** Creative Commons **Attribution-Share Alike 4.0** — fine for
  personal/desktop use; we add an attribution note in the README and
  settings (§3.1).
- **Download (done):** downloaded from
  `https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz`
  and placed in `dictionaries/cedict_1_0_ts_utf-8_mdbg.txt.gz` (3.8 MB
  gzipped, 125,396 entries, gzip integrity verified). Spot-checked lookups
  by simplified headword all resolve: 厨房 → `/kitchen/`, 学习 →
  `/to learn; to study/`, 电脑 → `/computer/`, 因为 →
  `/because; owing to; on account of/`, 恶劣 →
  `/vile/nasty/of very poor quality/`, 北京 → `/Beijing municipality…/`.

---

## 3. New module: `DictionaryService`

New file: `src/langread/services/dictionary.py`

```python
@dataclass(frozen=True)
class DictEntry:
    headword: str        # simplified headword (as in the app's words.text)
    pinyin: str | None   # normalised: "chú fáng" (tone marks, spaces)
    definition: str      # English, senses joined, capped

class DictionaryService:
    def __init__(self, cedict_path: Path): ...
    def lookup(self, word: str) -> DictEntry | None: ...
```

### 3.1 Bundling and installation

- Unpack the downloaded `.gz` once and commit/import
  `dictionaries/cedict_1_0_ts_utf-8_mdbg.txt` as
  `src/langread/resources/dictionaries/cedict.txt` (read-only resource, like
  `resources/hsk/hsk.csv`; ~10 MB plain text — or keep it gzipped in the
  package and decompress at load time to keep the installer at ~4 MB;
  decompression is < 1 s).
- Add `"resources/dictionaries/*"` to `[tool.setuptools.package-data]` in
  `pyproject.toml` (PyInstaller picks it up via the existing
  `--collect-data langread` command).
- No extraction/install step is needed at runtime (unlike v1's zip): the
  service reads the resource directly. The first `lookup()` (or app start,
  off the UI thread) parses the file once into memory.
- Attribution: `resources/dictionaries/README.txt` — "CC-CEDICT,
  CC-BY-SA 4.0, https://cc-cedict.org" — plus a line in the app README.

### 3.2 Parsing and lookup

- **Parse (once):** read the file line by line; skip `#` comment lines
  (header); split each line on spaces into `traditional`, `simplified`,
  `[pinyin]`, `/glosses/`. Build one dict keyed by the **simplified** form
  (`{simplified: entry}`). Where several entries share the same simplified
  headword (homographs/readings — e.g. 的 has 4 entries), keep the first and
  append the rest's senses to the same entry. 125k lines parse in well under
  a second.
- **Lookup:** exact match on the simplified key → hit; otherwise miss
  (`None`). A traditional form never appears in the app, so no secondary
  index is needed (optional: also index traditional forms — cheap, and
  future-proof if lesson text is ever pasted in traditional).
- **Pinyin conversion** (`pin1 yin1` → `pīn yīn`): a small utility
  (~30 lines) applies the standard tone-mark placement rules (a/o/e take
  the mark; otherwise the last vowel; `iu`→`u`, `ui`→`i`; tone 5 → no
  mark; `u:` → `ü`; drop the `·` name separators). This matches the tone
  mark style used by the HSK CSV and `pypinyin`.
- **Definition composition:** split the `/…/` field into senses; join the
  first **3 senses** with `"; "` and cap at **200 characters**. Keep the
  parenthesised meta-information (it disambiguates: "capital (city)").
  Strip classifier references (`, CL:…`) to keep entries short. Entries
  whose only gloss is "variant of X"/"old variant of X" are deprioritised
  when a better entry exists for the same headword, otherwise kept.
- **Failure tolerance:** missing/corrupt file → the service disables itself
  (`lookup()` always returns `None`) and logs a warning; the app silently
  behaves exactly as today. Never raises into the UI.
- **Thread-safety:** parse once at startup (off the UI thread, §4.1);
  afterwards the service is read-only, safe from worker threads.

---

## 4. Wiring the dictionary into the app

### 4.1 `TranslationService` — lookup order (core change)

`TranslationService.__init__` gains an optional
`dictionary: DictionaryService | None = None`. `translate_word()` becomes:

```
1. dictionary.lookup(word) → hit: return (entry.pinyin, entry.definition)
2. llm configured? → existing chat_json flow (unchanged)
3. else → (None, None)  (caller's pypinyin fallback still applies)
```

Construction sites updated (3 places, all already build an `LlmClient`):
`ui/lesson_create/generate_view.py` (×2) and `ui/workers.py`. A module-level
cached `get_dictionary()` helper (parses on first call, off the UI thread)
constructs the service; it is `None` if the resource is missing.

Because `lesson_saver._word_translation()` calls
`TranslationService.translate_word`, lesson saves automatically become
dictionary-first with **no change** to `LessonSaver`.

### 4.2 Word import — instant offline definitions

`WordImportService._create_word` / `link_hsk_entry`: after creating a word,
if `dictionary.lookup(text)` hits, fill pinyin+definition immediately
(offline, instant, no LLM round-trip). Priority for a *new* word becomes:

1. dictionary (always tried first, also when an HSK entry exists)
2. HSK entry (existing `link_hsk_entry` behaviour — fills only blanks)
3. nothing yet → LLM fills it at lesson-save time (existing behaviour)

`link_hsk_entry` keeps linking `hsk_word_id` and syncing `app_state`
unchanged; only the definition/pinyin *source priority* changes.

### 4.3 Schema v3 (optional but recommended): `definition_source`

Migration in `db/connection.py` (following the `v2` pattern) + `schema.sql`:

```sql
ALTER TABLE words ADD COLUMN definition_source TEXT
    CHECK (definition_source IN ('dictionary', 'llm', 'hsk', 'manual'));
```

`WordsRepo.set_translation` gains a `definition_source` argument. Every write
path records where the definition came from. This makes future refreshes
selective (`WHERE definition_source != 'dictionary'`) and lets the word
popup show a small "(dict)" badge. The `Word` dataclass gains the field with
a `None` default so all existing constructors keep working.

---

## 5. Refresh of all existing definitions (the overwrite)

Two entry points, one shared implementation.

### 5.1 Shared service: `DefinitionRefreshService`

New file: `src/langread/services/definition_refresh.py`

```python
class DefinitionRefreshService:
    def __init__(self, conn, dictionary, llm: LlmClient | None = None): ...
    def refresh(self, *, use_llm: bool, include_hsk: bool,
                progress: ProgressFn | None) -> RefreshReport
```

Algorithm (for every row in `words`, all three lists):

1. `dictionary.lookup(text)` → hit: overwrite `pinyin` (if the dictionary
   has one) and `definition`, set `definition_source='dictionary'`.
2. miss + `use_llm`: call `translate_word` (rate-limited, ~1 req/s); on
   success overwrite and mark `'llm'`; on LLM error leave the word for a
   later run (the report lists the misses).
3. miss + no LLM: clear the old (bad) definition, leave `definition=NULL`
   so it is visibly missing and will be retried at the next lesson save /
   refresh run.

Guardrails:

- **Automatic DB backup first** (`backups_dir()`, same mechanism as the sync
  import) — the overwrite is destructive by design.
- `include_hsk=True` also refreshes `hsk_words.definitions` so the HSK
  browser and future `link_hsk_entry` fills get the good data too
  (dictionary first, existing CSV value kept if the dictionary misses).
- Runs inside a `QThread` worker with the existing progress-dialog pattern;
  the report shows: refreshed-from-dictionary / refreshed-from-LLM / not
  found / cleared counts.

### 5.2 CLI script: `scripts/refresh_definitions.py`

For running against the live DB without launching the GUI (mirrors
`scripts/test_connections.py` conventions — honours `LANGREAD_DATA_DIR`):

```bash
.venv/bin/python scripts/refresh_definitions.py --dry-run   # report only
.venv/bin/python scripts/refresh_definitions.py             # dictionary only
.venv/bin/python scripts/refresh_definitions.py --with-llm --include-hsk
```

`--dry-run` prints the planned per-word changes; the script always takes a
backup before writing.

### 5.3 In-app menu action

Main menu → new item **"Refresh word definitions…"** opening a small dialog:
checkboxes *Use translation model for words not in the dictionary* (disabled
with a hint if the model isn't configured) and *Also refresh HSK list
definitions*, then runs §5.1 behind a progress dialog. This stays available
for re-runs (e.g. after a dictionary update).

---

## 6. Testing

New tests (all offline, per repo convention):

- `tests/unit/test_dictionary.py` — a small hand-written cedict.txt fixture
  (entries: plain word, homograph with two readings, proper noun with
  capitalised pinyin, `u:`/ü, `CL:` strip, variant-of entry): line parsing,
  simplified-key lookup, pinyin tone-mark conversion (including ü, tone 5,
  iu/ui rules), sense cap, CL stripping, missing-file → disabled service.
- `tests/unit/test_translation.py` — dictionary hit returns immediately and
  the stub LLM records **zero** calls; miss falls through to the LLM; both
  absent → `(None, None)` (existing assertions unchanged).
- `tests/unit/test_word_import.py` — new words get dictionary definitions at
  import time; HSK linking still happens.
- `tests/integration/test_lesson_saver.py` — existing expectations
  (`DEF[...]`) unchanged (no dictionary in the fixture); add one case with a
  stub dictionary overriding the stub translation.
- `tests/unit/test_definition_refresh.py` — temp DB with words from mixed
  sources: dry-run reports, dictionary overwrites, misses cleared or
  LLM-filled, backup file created, `include_hsk` refresh.
- Migration test for v3 (`definition_source` column added, backfills NULL).

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest` — the full suite must stay
green (existing tests use their own fixtures; `get_dictionary()` must respect
an env/arg override so tests can point it at a fixture or disable it).

Smoke check: `--smoke-test` also verifies the cedict resource is present and
parseable (first N lines).

---

## 7. Open decisions (please confirm before implementation)

1. **Sense cap**: first 3 senses / 200 characters (§3.2) — adjustable.
2. **Refresh scope**: `words` only, or `words` + `hsk_words` (§5.1)? Plan
   default: both.
3. **Pinyin overwrite policy**: when a word already has good pinyin and the
   dictionary also has pinyin, overwrite or keep? Plan default: overwrite
   both together (single authoritative source).
4. **Packaging**: ship `cedict.txt` uncompressed (~10 MB in the installer)
   or gzipped (~4 MB, +1 s at first load)? Plan default: gzipped.
5. **Proper nouns**: CC-CEDICT includes many names/places; they are kept
   (they are legitimate lookups), but we do **not** let the refresh's LLM
   fallback invent definitions for them.

---

## 8. Implementation order

0. ~~You download CC-CEDICT~~ — **done**: the file already sits in
   `dictionaries/cedict_1_0_ts_utf-8_mdbg.txt.gz` (verified).
1. `DictionaryService` + parser + tone-mark utility + tests (no app changes).
2. Resource bundling + `get_dictionary()` loader + pyproject/package-data.
3. `TranslationService` dictionary-first lookup + call-site updates + tests.
4. Word-import dictionary fill + tests.
5. Schema v3 `definition_source` + repo/dataclass updates + migration test.
6. `DefinitionRefreshService` + CLI script + tests.
7. In-app "Refresh word definitions…" UI + worker.
8. Run `scripts/refresh_definitions.py` on the live DB (after its automatic
   backup) and spot-check ~20 words in the review popup.
9. Update `README.md` (dictionary source, attribution, new menu item) and
   rebuild the PyInstaller bundle to confirm the resource ships correctly.

---

## Appendix: what was rejected and why

- **MengDict-DB-0.1** (§2.1): empty schema; character-level Unihan-2002
  data only; no word definitions.
- **reader.dict ZH zh-zh** (×5 formats, v1 plan): Chinese-language
  definitions in mostly traditional script; violates the English +
  simplified-only requirements.
