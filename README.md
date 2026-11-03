# LangRead — Chinese reading & listening app with spaced repetition

A desktop app (Windows/Linux) for an intermediate learner of Chinese: read
lesson text while listening to synchronized audio, with new words introduced
one at a time and reused across lessons via a spaced-repetition scheduler.
No flashcards — acquisition happens through exposure. Lessons are generated
by an external LLM (LM Studio / any OpenAI-compatible endpoint) and narrated
by an OpenAI-compatible TTS server (Kokoro).

Requirements and design: see `20261101_language_app_reqs.md` (v1.1) and
`20261101_desktop_app_plan.md`.

## Quick start (Linux)

```bash
cd ~/lang_read_app
python3 -m venv .venv
.venv/bin/pip install -e .        # use a mirror if needed (see below)
.venv/bin/langread                # run the app
```

PyPI mirror (this machine): `~/.config/pip/pip.conf` →
`https://mirrors.aliyun.com/pypi/simple/` (Tsinghua's mirror returned 403s).

Run the tests:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest
```

## First use

1. **Model settings** (menu → *Model settings*): enter the base URLs for
   your **sentence generation** model (LM Studio, e.g.
   `http://<host>:1234/v1`), **translation** model, and **TTS** server
   (Kokoro, e.g. `http://<host>:8880/v1`), plus model names and a Chinese
   voice. Press *Test connection* on each.
2. **Create a new topic** (menu → *Manage topics* → *New topic…*; topics can
   be renamed, and empty topics deleted, from the same window).
3. **Add words**: paste Chinese text (tick the words that are new to you —
   the rest go to the Basic list), enter words one by one, or bulk-add from
   the bundled **HSK 1–6 lists** (4,991 words with pinyin and definitions).
4. **Create a new lesson**: menu → *Manage lessons* → pick the topic →
   *New lesson…*: accept or change the suggested
   words, generate paragraph by paragraph, hand-edit the text or word
   segmentation if needed, then **Approve & save** (audio, translations and
   word promotion happen automatically; an interrupted save can be resumed).
5. **Review a lesson** (*Manage lessons* → *Review lesson*): read along while
   the audio plays (speed control,
   ±15s), tap any word for pinyin/definition/list status, toggle sentence
   translations, then rate the words (difficult/easy/standard/unchanged) to
   drive the spaced repetition. *Manage lessons* also lets you edit a
   lesson's text, regenerate its audio, and delete the last lesson of a
   topic (its new words return to the New list).
6. **Sync with Android**: export a sync bundle and copy it to the phone over
   USB; import the phone's results bundle back (verified + auto-backup).

## Data, backups, safety

- Database, audio and backups live in `~/.local/share/LangReadApp/`
  (Windows: `%LOCALAPPDATA%\LangReadApp`). Override with `LANGREAD_DATA_DIR`.
- Every sync import takes an automatic DB backup first (`backups/`).
- Interrupted lesson saves leave the lesson *incomplete* and are resumable.

## Packaging (PyInstaller)

Linux:

```bash
scripts/build_desktop.sh
QT_QPA_PLATFORM=offscreen LANGREAD_DATA_DIR=/tmp/smoke dist/LangRead/LangRead --smoke-test
```

Windows (in PowerShell, from the repo root, after `pip install -e .`):

```powershell
.venv\Scripts\pyinstaller --noconfirm --name LangRead --windowed --collect-data langread src\langread\main.py
$env:QT_QPA_PLATFORM="offscreen"; $env:LANGREAD_DATA_DIR="$env:TEMP\langread-smoke"; dist\LangRead\LangRead.exe --smoke-test
```

The `--smoke-test` flag boots the app, applies the schema, seeds the prompt
templates, imports the HSK dataset, and exits 0 on success.

## Testing

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest    # 201 tests
```

Unit and integration tests cover the SRS engine, segmentation, generation
pipeline, save pipeline, sync round-trips, and all UI flows — model endpoints
are exercised against a local fake OpenAI-compatible server, so no network is
needed.

## Project status

Desktop app (milestones M0–M10) is complete: all §12.1 functions work.
The Android app is the next phase — see `20261101_android_app_plan.md`
(Flutter; starts only after the desktop app is in production use).
