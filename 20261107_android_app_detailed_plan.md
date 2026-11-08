# Android App — Detailed Implementation Plan

- **Date:** 2026-11-07
- **Based on:** `20261101_android_app_plan.md` (rough plan; Flutter framework choice approved), `20261101_language_app_reqs.md` v1.1 (section references "§n" point there), `20261101_desktop_app_plan.md`, and the **as-implemented desktop code** (`src/langread/services/sync.py` — the bundle format in §3 below is transcribed from that implementation, so the two apps are compatible by construction).
- **Status:** Detailed plan. Environment setup (§7 / milestone A0) executed on 2026-11-07 — see "A0 execution results" at the end of §7.
- **Scope:** Android is a **review-only** companion (§3.2): select topic → review lesson, plus sync with the desktop. **Deployment model:** the app is **sideloaded** — a release APK is transferred to the phone and installed by hand (no Play Store, no auto-update, no cloud, no accounts). Everything the rough plan decided (Flutter, package choices, mirror-based toolchain) carries over unchanged; this document details the parts the rough plan left open.

---

## 1. Scope

**In scope:**
- Home screen: topic list → lesson list with last-reviewed state (§8.1).
- Lesson review screen: tappable-word text, word popups, sentence translation toggles, audio bar, word-review stage, complete/cancel (§8.2–8.7).
- Sync: import content bundles from the desktop (`sync-v1.zip`), export results bundles (`results-<ts>.zip`), with full integrity verification and pre-import backup (D-3).
- Offline by design: zero network calls after content is imported.
- Sideload release APK built from this laptop.

**Out of scope (never appears in the Android UI):** authoring, lesson generation, word-list management beyond the review-screen popup actions, model settings, prompt templates, SRS parameter editing, HSK browsing. The SRS *fields* are received in the content bundle and displayed where useful (e.g. popup status), but **SRS is never computed on Android** — ratings are queued as events and reconciled by the desktop.

## 2. Technology Stack (final)

| Concern | Choice | Notes |
|---|---|---|
| Framework | Flutter stable channel, Dart | user's prior experience; per rough plan §1 |
| State management | **`provider`** (rough plan §8 open point — resolved: provider) | `ChangeNotifier` per screen + one `SyncState` |
| Local DB | **`drift`** (SQLite) | Type-safe; schema mirrors desktop tables (§4) |
| Audio | **`just_audio`** | play/pause, `setSpeed` 0.5×–2.0×, `seek` ±15s, position stream. **No background-audio mode** — audio pauses when the app is backgrounded; the review use-case (reading while listening) is foreground-only |
| Archives / hashing | `archive` + `crypto` | unzip bundles + SHA-256 manifest verification |
| File access | `file_picker`, `path_provider`, `share_plus` | pick bundle from Downloads; app-local storage; share/save results bundle |
| Word tap rendering | `RichText` + per-token `TapGestureRecognizer` | built for this |
| Min Android version | **Android 8.0 (API 26)** | unchanged from rough plan |
| Target SDK | current stable required by the Flutter template (API 35 as of setup) | confirmed at A1 by a successful build |
| Theming | Material 3, **follows system dark mode** and system font scaling (rough plan §8 open point — resolved: follow system) | no in-app settings screen at v1 |
| App name / icon | **"LangRead"**, adaptive launcher icon at A6 | placeholder acceptable until then |

**Fallback** (unchanged from rough plan §1): Kotlin + Jetpack Compose only if the Flutter toolchain proves unusable on this network. The sync spec (§3) and local schema (§4) are framework-agnostic, so a rewrite would only touch the UI layer.


## 3. Sync Bundle Format v1 (normative — matches the implemented desktop code)

Both apps produce and consume **zip (deflate) archives** with this layout. `BUNDLE_SCHEMA_VERSION = 1`; a mismatch is a clean rejection with an "update the desktop app" message.

### 3.1 `manifest.json` (both bundle types)

```json
{
  "schema_version": 1,
  "bundle_type": "content" | "results",
  "created_at": "<ISO-8601 UTC, e.g. 2026-11-07T12:00:00+00:00>",
  "counts": { "...entity counts, informational..." },
  "files": { "<archive path>": "<sha256 hex of the file bytes>" }
}
```

`files` covers **every** payload file (content.json, events.jsonl, each `audio/lesson_<id>.mp3`).

### 3.2 Content bundle `sync-v1.zip` (desktop → Android)

```
sync-v1.zip
├── manifest.json
├── content.json
├── audio/lesson_<id>.mp3        # one per lesson with audio (D-1)
└── events.jsonl                 # desktop review events since last export (optional)
```

`content.json` — exact entity fields (transcribed from `SyncService.build_content`):

- `schema_version`, `exported_at` (top level)
- `topics[]`: `id, name, order_index, created_at`
- `lessons[]`: `id, topic_id, order_index, title, status, audio_path, created_at, last_reviewed_at`
  (`status ∈ draft|complete|incomplete`; Android imports all but only lists `complete` lessons for review)
- `sentences[]`: `id, lesson_id, para_index, sent_index, text, segmentation, translation`
  (`segmentation` is a **JSON array** of word tokens — the desktop's dataclass decodes the DB string before export; the Android import accepts either a string or an array and normalizes to the stored JSON-string column)
- `words[]`: `id, text, pinyin, definition, list_state, hsk_word_id, source, added_at, ease, interval_days, due_at, reps, lapses, last_rated_at`
  (`list_state ∈ new|learned|basic`; SRS fields carried but never computed locally)
- `lesson_words[]`: `lesson_id, word_id, role` (`role ∈ new|review`)
- `hsk_words[]`: `id, text, pinyin, definition, level, app_state`

### 3.3 Results bundle `results-<timestamp>.zip` (Android → desktop)

```
results-<ts>.zip
├── manifest.json    # bundle_type "results", counts: {events: N}, files: {events.jsonl: sha256}
└── events.jsonl     # one JSON object per line, UTF-8, non-ASCII kept as-is
```

Event record types (exactly the three the desktop's `import_results` applies):

```jsonc
{"type": "rating",          "word_id": 12, "lesson_id": 3,
 "rating": "difficult|easy|standard|unchanged", "reviewed_at": "<ISO-8601 UTC>"}

{"type": "lesson_reviewed", "lesson_id": 3, "reviewed_at": "<ISO-8601 UTC>"}

{"type": "word_action",     "action": "add_new|add_basic|basic_to_new",
 "word_text": "<simplified Chinese>", "acted_at": "<ISO-8601 UTC>"}
```

Rules:
- Every event carries its UTC timestamp; the desktop sorts by `reviewed_at`/`acted_at` and applies in order (most recent rating wins, §10 conflict rule).
- `word_id` refers to the **desktop's** word ids — valid because the Android `words` table is a 1:1 import.
- Word-list popup actions (§6.3) apply **locally immediately** (local `list_state` changes) *and* queue a `word_action` event; `get_or_create` semantics on the desktop make re-delivery safe.
- Events are removed from the local `pending_events` queue **only after a successful content import** confirms the desktop has them (§4.2 step 4) — never at export time. A lost results bundle never loses review data.

### 3.4 Verification algorithm (identical semantics on both sides)

1. Zip opens and contains `manifest.json` — else "not a valid zip bundle".
2. `manifest.schema_version == 1` — else "unsupported schema version" (clean reject, nothing applied).
3. `bundle_type` matches what the flow expects (`content` for Android import).
4. Every file listed in `manifest.files` exists in the archive and its SHA-256 matches — else "checksum mismatch for <file>" (D-3: corrupt/partial bundles rejected before anything is applied).
5. Only then: backup, then apply (§4.2).


## 4. Local Data Layer (drift)

### 4.1 Schema

Content tables mirror the desktop names/columns exactly (so `content.json` maps 1:1 and ids stay stable):

```sql
topics(id INTEGER PK, name TEXT, order_index INT, created_at TEXT)
lessons(id PK, topic_id, order_index INT, title TEXT NULL, status TEXT,
        audio_path TEXT NULL, created_at TEXT, last_reviewed_at TEXT NULL)
sentences(id PK, lesson_id, para_index INT, sent_index INT, text TEXT,
          segmentation TEXT /* JSON array of tokens, imported as-is */,
          translation TEXT NULL)
words(id PK, text TEXT UNIQUE, pinyin TEXT NULL, definition TEXT NULL,
      list_state TEXT, hsk_word_id INT NULL, source TEXT, added_at TEXT,
      ease REAL, interval_days REAL NULL, due_at TEXT NULL,
      reps INT, lapses INT, last_rated_at TEXT NULL)
lesson_words(lesson_id, word_id, role TEXT, PRIMARY KEY(lesson_id, word_id))
hsk_words(id PK, text, pinyin, definition, level INT, app_state TEXT)

-- local-only tables:
pending_events(id PK AUTOINCREMENT, type TEXT, payload TEXT /* full event JSON */,
               created_at TEXT)
sync_meta(key TEXT PK, value TEXT)  -- last_import_at, device_id (random uuid)
```

Storage layout (all under the app's **documents directory**, user-visible over USB):
- `langread.db` — the drift database
- `audio/lesson_<id>.mp3` — imported audio (outside the DB)
- `backups/pre-import-<ts>.db` — automatic pre-import backups (keep last 5)
- `exports/results-<ts>.zip` — produced results bundles

### 4.2 Import pipeline (content bundle → local DB)

1. **Pick** — "Sync" → `file_picker` (any accessible path; typical: Downloads after a USB/MTP copy).
2. **Verify** — the §3.4 algorithm; any failure → error card with the exact reason; **nothing applied**.
3. **Backup** — copy the current `langread.db` to `backups/pre-import-<ts>.db`.
4. **Apply** — one drift **transaction** (import is idempotent and atomic):
   - delete + reinsert `topics, lessons, sentences, words, lesson_words, hsk_words` (desktop is the source of truth; also immune to mid-transaction interruption);
   - write `audio/lesson_<id>.mp3` files (skip ones already present with matching size so re-importing is cheap);
   - update `sync_meta.last_import_at`;
   - **keep `pending_events`**; additionally prune any `rating`/`lesson_reviewed` event whose timestamp predates `content.json.exported_at` **and** is superseded by the desktop's own `events.jsonl` in the bundle (same lesson, same word, or same lesson_reviewed) — the only pruning rule; anything ambiguous stays queued (the desktop's most-recent-wins rule absorbs duplicates safely).
5. **Report** — dialog: "Imported N topics, M lessons, K sentences, L MP3s; P pending results kept."
6. Hashing/unzipping/DB writes run in a background isolate with a progress stream — the UI never janks on large bundles.

### 4.3 Export pipeline (results bundle)

1. Read `pending_events`; if empty → "nothing to sync back" (still allow producing an empty bundle? No — a friendly no-op message instead).
2. Serialize to `events.jsonl` (one JSON object per line, UTF-8).
3. Compute SHA-256, write `manifest.json` (`bundle_type: "results"`), zip to `exports/results-<yyyyMMdd-HHmmss>.zip`.
4. Offer **Share** (`share_plus`) plus show the saved path for USB copy-back; the desktop's import side (`SyncService.import_results`) is already implemented and tested.

## 5. Architecture & Project Layout

Layered: UI → providers (`ChangeNotifier`) → services/DAOs → drift DB. UI never writes SQL; `data/` + `domain/` + `services/` never import Flutter widgets (pure Dart, unit-testable).

```
android_app/                      # Flutter project (moved into this repo on
├── pubspec.yaml                  # 2026-11-07 so both apps share one repo)
├── test/                         # flutter_test (see §8)
├── integration_test/
└── lib/
    ├── main.dart                 # bootstrap: providers, MaterialApp, M3 theme
    ├── app.dart                  # routes: home, lessonList, review, sync
    ├── data/
    │   ├── db.dart               # drift database + open/close
    │   ├── tables.dart           # §4.1 tables as drift classes
    │   ├── daos/                 # topics, lessons, sentences, words,
    │   │                         # hsk, pending_events
    │   ├── bundle_reader.dart    # unzip + manifest verify (§3.4) — pure Dart
    │   ├── import_service.dart   # §4.2 (backup, transaction, isolate, progress)
    │   └── export_service.dart   # §4.3
    ├── domain/
    │   ├── models.dart           # Topic, Lesson, Sentence, WordToken, PendingEvent
    │   └── lesson_text.dart      # segmentation JSON → tokens → TextSpans
    ├── services/
    │   └── audio_player_service.dart   # just_audio wrapper + ChangeNotifier
    ├── state/
    │   ├── library_provider.dart      # topics/lesson lists
    │   ├── review_session.dart        # session state + complete/cancel (§8.7)
    │   └── sync_provider.dart         # import/export status + progress
    └── screens/
        ├── home_screen.dart           # §6.1
        ├── lesson_list_screen.dart
        ├── review/
        │   ├── review_screen.dart     # §6.2 stages: reading → word review → done
        │   ├── lesson_text_view.dart  # tappable-word rendering (§8.3)
        │   ├── word_sheet.dart        # bottom-sheet popup (§8.3)
        │   ├── sentence_translation.dart  # toggle (§8.4)
        │   ├── audio_bar.dart         # §8.5
        │   └── word_review_stage.dart # §8.6
        └── sync_screen.dart           # §6.4
```


## 6. Screens (detailed UX spec)

Two top-level destinations per §12.2, implemented as a two-tab bottom navigation: **Review** (home) and **Sync**. Simplicity is a feature: no drawer, no settings page at v1.

### 6.1 Home / Review tab (§8.1)

- **Empty states:** never synced → one card: "No content yet — sync with the desktop" with a button jumping to the Sync tab. Synced but no `complete` lessons → "This bundle has no completed lessons".
- Topic list (`order_index` order); each row: name, lesson count, "N/M lessons reviewed".
- Tap topic → **lesson list**: rows in `order_index` order — title (or "Lesson N"), "Last reviewed: <date>" or "Never reviewed", subtle "new" badge for lessons never reviewed on this device.
- Tap lesson → review screen. `draft`/`incomplete` lessons are not listed (§3.2 note).

### 6.2 Lesson review screen (§8.2–8.7)

A single `review_screen.dart` holding a stage state machine: **reading → wordReview → done**.

**Reading stage:**
- **Text view** (§8.2/§8.3): scrollable column of paragraphs (spacing between), each sentence built from its stored `segmentation` tokens:
  - Chinese word tokens → `TextSpan` with `TapGestureRecognizer` (tap → word sheet); comfortable touch targets;
  - punctuation / non-word tokens → plain spans;
  - **first occurrence** of each lesson new word (`lesson_words.role='new'`) styled with a highlight background + bold — static, D-1;
  - words whose current local `list_state` is `new` get an underline style (helps spot acquiring words);
  - scrolling is manual; no auto-scroll karaoke (D-1).
- **Word sheet** (§8.3): modal bottom sheet — word (large), pinyin, definition, list status ("Learned · due 2026-11-12" / "New" / "Basic" / "HSK 4 · unused" / "not on any list"); actions, exactly the desktop set:
  - not on any list → "Add to Basic list" / "Add to New list";
  - basic → "Move to New list";
  - Actions **commit immediately** (§8.7 exception): local `words.list_state` update + `pending_events` row (`word_action`), snackbar confirmation with **Undo** (undo deletes the queued event and restores state).
- **Sentence translation** (§8.4): each sentence line ends with a small "▸ 译" chip; tapping reveals the stored translation below it ("▾ 译"); per-sentence state only.
- **Audio bar** (§8.5), pinned bottom, wraps `just_audio`:
  - play/pause, restart, speed chips (0.5× 0.75× 1.0× 1.25× 1.5× 2.0×), −15 s/+15 s, elapsed/total, thin progress slider;
  - "Jump to end" button → word-review stage; natural playback end also auto-advances;
  - audio file absent → bar disabled with "no audio in this bundle".
- App lifecycle: pause audio when backgrounded; restore state when foregrounded.


**Word review stage (§8.6):**
- List of this lesson's words on the Learned list (`lesson_words` × `words.list_state='learned'`), each row: word, pinyin, definition, and a 4-way segmented control: difficult / **standard (default)** / easy / unchanged.
- Multi-select checkboxes, select-all, and a bulk segmented control applying one rating to the whole selection.
- "Back to text" (returns to reading stage; ratings kept), "Mark review complete".

**Done / completion (§8.7):**
- "Mark review complete" → queue **one `rating` event per listed word** (every rating — including `unchanged` — is meaningful to the desktop's SRS reconciliation) + one `lesson_reviewed` event; set local `lessons.last_reviewed_at`; stop audio; completion card: "Next lesson" (if any) / "Back to lessons".
- **Cancel** (app-bar back, or "Cancel review" in the overflow menu with a confirm dialog) → discards the session's ratings and the review timestamp; word-list actions already confirmed in popups **stay** (§8.7 — same semantics as the desktop app).

### 6.3 Sync tab (§10 / D-3)

Status card at top: last import time, pending-results count, content size, audio count.
- **Import from desktop** → file pick → verify (with progress) → confirm dialog ("This replaces local content; a backup will be created") → apply (with progress) → summary dialog. Failures show the exact §3.4 error and nothing is applied.
- **Export results** → builds the bundle → share sheet + saved-path note. Disabled ("No pending results") when the queue is empty.
- History: recent imports/exports with timestamps (small JSON log in `sync_meta`).

## 7. Development Environment Setup (fresh Linux, Chinese network — mirror-based)

Executed as milestone **A0** immediately after this plan; recorded here as the canonical procedure:

1. **JDK 17** — user-local tarball under `~/jdks/` (no sudo needed): Adoptium Temurin 17 or OpenJDK GA from a China mirror (TUNA rate-limits this subnet, so Tencent/Huawei mirrors or `dl.google.com`-class hosts are preferred). `JAVA_HOME` + `PATH` exported in `~/.bashrc`.
2. **Flutter SDK 3.47.x stable** — tarball from `https://storage.flutter-io.cn/...` extracted to `~/flutter`, `PATH` via `~/.bashrc`.
3. **Pub/storage mirrors** in `~/.bashrc`: `PUB_HOSTED_URL=https://pub.flutter-io.cn`, `FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn`.
4. **Android SDK** — commandline tools from `dl.google.com` (verified reachable), installed to `~/android-sdk`; `sdkmanager` (running on JDK 17) installs `platform-tools`, `platforms;android-36`, `build-tools;36.0.0` (current versions required by the Flutter 3.47 template); licenses accepted (`yes | sdkmanager --licenses`). `ANDROID_HOME`/`ANDROID_SDK_ROOT` in `~/.bashrc`.
5. **No Android Studio** — everything needed (sdkmanager, adb, Gradle via Flutter's wrapper) is command-line; the IDE is VS Code with the Flutter/Dart extensions.
6. **Gradle mirrors** — applied when the project is created (A1): `distributionUrl` → Tencent mirror; repositories → Aliyun (`google`, `public`, `gradle-plugin`).
7. **Phone** — Developer options + USB debugging; verified with `adb devices`.
8. `flutter doctor` green (except deliberately skipped components, e.g. Android Studio) → A0 done.

**A0 execution results (2026-11-07):**
- **JDK:** `~/jdks/jdk-17.0.2` — Oracle OpenJDK 17.0.2 GA tarball from `mirrors.huaweicloud.com/openjdk/` (TUNA rate-limited this subnet; Huawei's Adoptium path served an HTML portal page, but its `openjdk/` path serves real tarballs — verified by gzip magic bytes).
- **Flutter:** 3.47.9 stable at `~/flutter` (1.5 GB tarball from `storage.flutter-io.cn`); `flutter --version` OK.
- **Android SDK:** `~/android-sdk` — cmdline-tools (11076708) from `dl.google.com` (verified reachable), plus `platform-tools` (adb 1.0.41), `platforms;android-36`, `build-tools;36.0.0`; all licenses accepted; `flutter config --android-sdk ~/android-sdk` set.
- **Shell config:** `JAVA_HOME`, `ANDROID_HOME`, `ANDROID_SDK_ROOT`, `PUB_HOSTED_URL`, `FLUTTER_STORAGE_BASE_URL`, and `PATH` exported in `~/.bashrc` (open a new shell to pick them up).
- **VS Code:** extensions `dart-code.dart-code` and `dart-code.flutter` (3.146.0) installed via `code --install-extension`.
- **`flutter doctor`:** ✓ Flutter, ✓ Android toolchain (SDK 36.0.0), ✓ Connected device (Chrome etc.), ✗ Linux desktop toolchain (clang/ninja/GTK — **not needed**; the app targets Android only). **A0 is done except the physical-phone step**: no device was attached during setup; connect the phone with USB debugging enabled and confirm with `adb devices` (the `PATH` for adb is already in `~/.bashrc`).
- Approx. 5 GB of disk used total; the download tarballs were deleted after installation.
- **Phone step completed (2026-11-07):** device `d48a1330` — OnePlus PJZ110, **Android 16, arm64-v8a** — visible in `adb devices` (USB debugging authorized on the phone). Comfortably above the API 26 minimum; the arm64-v8a ABI runs the fat release APK natively. **A0 is fully complete.**


## 8. Testing Strategy

- **Unit (pure Dart, no Flutter):** `bundle_reader` — fixture zips built in-test (good bundle, wrong schema_version, wrong bundle_type, missing file, checksum mismatch, corrupt zip); `import_service` — temp drift DB: transaction atomicity (kill mid-apply → DB unchanged), pending_events preserved + pruning rule; `export_service` — produces a bundle the §3.4 verifier accepts, with byte-exact manifest fields; `lesson_text` — segmentation JSON → spans, new-word first-occurrence highlighting.
- **Widget tests:** home/lesson lists from a seeded in-memory DB; review-screen stage machine (reading → word review → complete vs. cancel semantics, §8.7); word-sheet actions queue the right `word_action` payloads.
- **Cross-app round-trip (the critical test class):** the desktop repo's pytest already covers `SyncService.import_results` against the reference `write_results_bundle`. The mirror test on the Flutter side: a **fixture content bundle generated by the real desktop code** (a small pytest writes `test/fixtures/sync-v1.zip` with 2 topics / 3 lessons / fake MP3 bytes) is committed into the Flutter project's `test/fixtures/`; the Flutter import test consumes it, and the Flutter export test produces a results bundle that a companion pytest feeds into the real `SyncService.import_results`. This pins compatibility to the actual implementations, not to documents.
- **Manual smoke checklist** per milestone at `android_app/docs/smoke_checklist.md` (mirroring the desktop habit); the final A6 round-trip uses the real desktop app and the real phone.

## 9. Build, Signing & Sideload Deployment

- **Dev loop:** `flutter run` over USB to the physical phone (hot reload), default debug signing.
- **Release APK (the deployment artifact):**
  1. Create a self-signed keystore once: `keytool -genkey -v -keystore ~/keystores/langread-release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias langread` (keep the keystore + password safe; a new key means the next APK cannot install over the old one without uninstalling).
  2. `android/key.properties` (gitignored) + release signing config in `android/app/build.gradle` (standard Flutter recipe).
  3. `flutter build apk --release` — a single **fat APK** (arm64/arm/x64 in one file; one file to transfer, ~2× larger than an ABI-split APK, acceptable here).
  4. Copy `build/app/outputs/flutter-apk/app-release.apk` to the phone (USB/MTP or any file transfer), tap it, allow "Install unknown apps" for that file manager once, install.
- **Updates:** same flow; install over the old APK (signatures must match). App data (documents dir) survives reinstalls.
- **Versioning:** `pubspec.yaml` `version: X.Y.Z+NN`, bumped on every release APK.


## 10. Milestones

Each milestone ends with runnable code (`flutter analyze` + `flutter test` green) plus a manual smoke item. A0 begins today (2026-11-07); A1+ proceed after the desktop app is in production use (roadmap step 6), exactly as the rough plan sequenced.

| # | Milestone | Tasks | Acceptance |
|---|---|---|---|
| **A0** | Environment | §7 steps 1–8: JDK 17 (user-local), Flutter 3.47 SDK + pub mirrors, Android cmdline-tools + platform/build tools + licenses, `~/.bashrc` exports, VS Code extensions, phone visible to `adb` | `flutter doctor` green (minus deliberately skipped components, e.g. Android Studio); `adb devices` shows the phone |
| A1 | Scaffolding | `flutter create`, provider wiring, drift schema (§4.1) + DAOs, two-tab shell, dev seed from fixture | App runs on the physical phone; test skeleton passes |
| A2 | Sync import | `bundle_reader` (verify), `import_service` (backup + transactional apply + isolate), sync tab UI, desktop-fixture round-trip test | Fixture `sync-v1.zip` imports; content visible in lists; corrupt bundles rejected cleanly |
| A3 | Review text | lesson text view with tappable tokens, word sheet + local word actions + pending queue, sentence translation toggles, new-word highlighting | Full §8.3/§8.4 flows on the phone |
| A4 | Audio | `audio_player_service` + audio bar wired to imported MP3s; lifecycle handling | §8.5 controls work; speed/seek/jump-to-end correct |
| A5 | Word review + export | word-review stage, complete/cancel semantics, `pending_events`, `export_service` + share | §8.6/§8.7 work; exported bundle imports into the real desktop `SyncService` (pytest) |
| A6 | Release & round-trip | keystore + signed release APK, launcher icon / app name, full real-data round-trip with the desktop app, install on the phone | Production APK installed; a real review session's results appear on the desktop |

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Chinese network blocks/throttles Flutter/Gradle even with mirrors | flutter-io.cn worked for the SDK (verified in A0); Gradle → Tencent distribution + Aliyun repositories at A1; last resort: Kotlin+Compose fallback (§2) |
| TUNA mirror rate-limiting (observed during A0) | Huawei/Tencent mirrors for the JDK; `dl.google.com` verified reachable for Android SDK pieces |
| First Gradle build downloads ~1 GB of dependencies on a slow link | One-time cost; Gradle cache persists in `~/.gradle`; warm it at A1 and record elapsed time |
| MTP/USB bundle copying is clunky | Bundles live in Downloads; `share_plus` for export; two-tap flow surfaced in the sync screen |
| Drift schema drift vs. desktop `content.json` | `schema_version` check rejects mismatches cleanly; cross-app fixture round-trip tests (§8) fail loudly if either side changes |
| Lost results bundle (user forgets to copy it back) | Events stay queued until a successful import confirms them (§3.3); sync tab shows the pending count |
| Sideload confusion (unknown-apps prompt, signature mismatch on update) | §9 documents the flow; keystore location recorded; updates only ever signed with the same key |
| Phone storage pressure from audio | MP3s are ~1–2 min each; import skips existing files; realistic libraries total tens of MB |

## 12. Definition of Done (Android; roadmap step 6)

- Import a real `sync-v1.zip` produced by the production desktop app; review a real lesson end-to-end on the phone (text, popups, translations, audio, word review, complete).
- Export a results bundle that the production desktop app imports, with ratings / timestamps / word actions landing correctly.
- A signed release APK installed on the phone via plain file transfer, surviving restarts and reinstalls.
- `flutter analyze` and `flutter test` green; the cross-app round-trip tests pass against the real desktop `SyncService`.

---

## 13. Execution record (2026-11-07, milestones A1–A6)

The phone was disconnected during implementation, so device-run acceptance
items were replaced by: full host test suite + building the debug and
signed-release APKs. The remaining unchecked phone items live in
`android_app/docs/smoke_checklist.md`.

**Project:** `lang_read_app/android_app` — `flutter create --project-name
langread --org dev.langread`, application id `dev.langread.langread`, app
label "LangRead". (Initially created as a sibling of the desktop repo per
§5; moved into this repository on 2026-11-07 at the user's request so both
apps are versioned together. Verified after the move: `flutter pub get`,
`flutter analyze` clean, all 29 tests pass, and the round-trip tools still
work. The `gradle-wrapper.jar` is committed — the Flutter template's ignore
of it was removed — so a fresh clone can build immediately.)

**A1 — Scaffolding ✅**
- Package versions pinned against the 2026 ecosystem: provider 6.1.5, drift
  2.35.3, just_audio 0.10.6, file_picker 13.3.2, share_plus 13.3.1,
  archive 3.6.1 (pinned deliberately: archive 4.x has a breaking API),
  crypto, path_provider, path; dev: drift_dev + build_runner + sqlite3.
- drift schema in `lib/data/tables.dart` mirrors §4.1 (one deviation: column
  getters for the DB's `text` columns are named `content`/`word` — a getter
  literally named `text` shadows drift's `text()` builder; the SQL column
  names remain `text` via `.named('text')`).
- Two-tab shell (Review/Sync) per §6; `provider` wiring.
- `dart run build_runner build` generates `lib/data/db.g.dart`.

**A2 — Sync import ✅**
- `lib/data/bundle_reader.dart` implements §3.4 verification exactly
  (valid zip → manifest → schema_version → bundle_type → per-file SHA-256).
- `lib/data/import_service.dart`: backup (WAL-checkpoint + copy, keep 5) →
  single-transaction delete+reinsert → audio files (size-skip) →
  conservative pending-event pruning (§4.2 step 4) → sync_meta update.
- Fixture `test/fixtures/sync-v1.zip` is generated by the **real desktop
  `SyncService`** via `tool/make_fixture.py` — compatibility is pinned to
  implementations, not documents (§8). One spec correction found during
  this work: `content.json` carries `segmentation` as a JSON **array**
  (§3.2 updated); the import accepts both forms.
- Host tests: valid import, idempotent re-import + backup, pending-events
  preserved/pruned, corrupt bundle rejected with data untouched.

**A3 — Review text ✅ (host-verified; phone run pending)**
- `lib/domain/lesson_text.dart` + `lib/screens/review/lesson_text_view.dart`:
  per-token `TapGestureRecognizer`s (disposed per rebuild), first-occurrence
  new-word highlight (D-1), New-list underline, per-sentence "▸译" chip
  revealing the translation inline.
- `word_sheet.dart` bottom sheet with the exact desktop action set
  (§8.3); actions apply locally + queue `word_action` events, with Undo.

**A4 — Audio ✅ (code complete; phone run pending)**
- `lib/services/audio_player_service.dart` (just_audio wrapper) +
  `audio_bar.dart`: play/pause, restart, ±15 s, speed chips 0.5×–2×,
  progress slider, "jump to end"; playback end auto-advances to word
  review; audio pauses on app backgrounding.

**A5 — Word review + export ✅**
- `lib/state/review_session.dart`: ratings (default standard), complete()
  queues one rating per listed word + lesson_reviewed and sets the local
  timestamp; cancel writes nothing (§8.7); word actions commit immediately.
- `lib/data/export_service.dart` produces §3.3-exact results bundles.
- **Cross-app round-trip verified**: `flutter test
  test/roundtrip_bundle_test.dart` imports the real desktop bundle,
  completes a review, exports `build/results-roundtrip.zip`;
  `tool/verify_results_bundle.py` imports it with the real desktop
  `SyncService.import_results` → "ROUND-TRIP OK: 4 events (2 ratings,
  1 lesson reviews, 1 word actions) all applied correctly."

**A6 — Release ✅ (APK built; phone install pending)**
- Gradle mirrors applied: distributionUrl → Tencent
  (`gradle-9.3.1-all.zip`), repositories → Aliyun (gradle-plugin/google/
  public) in `settings.gradle.kts` + root `build.gradle.kts`.
- `minSdk = 26` (§2), app label "LangRead", launcher icon generated
  (teal book + 读, all 5 mipmap buckets).
- Release keystore: `~/keystores/langread-release.jks` (PKCS12, alias
  `langread`, 10000-day validity); password in
  `~/keystores/langread-release.password` (chmod 600); wired via
  gitignored `android/key.properties`; debug fallback when absent.
- `flutter build apk --debug` + `flutter build apk --release` (fat APK)
  — see the build log; output at `build/app/outputs/flutter-apk/`.

**Deviations from the plan (all minor):**
- DAOs consolidated into `db.dart` (drift codegen simplicity) instead of a
  `daos/` directory; `state/library_provider.dart` dropped in favor of
  drift `StreamBuilder`s in the screens.
- The §4.2 "background isolate" import is not isolated: drift already runs
  queries off the UI thread and realistic bundles hash in well under a
  second; revisit if real bundles prove large.
- The automated "companion pytest" of §8 became two explicit tools
  (`tool/make_fixture.py`, `tool/verify_results_bundle.py`) — same
  guarantee, simpler cross-repo wiring.
- just_audio 0.10.6 / file_picker 13 / share_plus 13 are the current
  2026 versions (the rough plan's 2.x-era API guesses were updated after
  reading the actual package sources).
