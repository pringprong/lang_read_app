# Android App — Rough Implementation Plan

- **Date:** 2026-11-01
- **Based on:** `20261101_language_app_reqs.md` v1.1 and `20261101_desktop_app_plan.md` (approved)
- **Status:** Rough plan (roadmap step 3). **Implementation is deliberately deferred until the desktop app is complete and in production use** (roadmap step 6).
- **Scope reminder:** Android is a **review-only** app (§3.2): select topic → review lesson, and sync with the desktop. No authoring, no word-list management, no model configuration.

---

## 1. Framework Choice

| Criterion | **Flutter (Dart)** ✅ recommended | Kotlin (native Android) | Python on Android (Chaquopy / Kivy / BeeWare) |
|---|---|---|---|
| User's prior experience | **Yes** — user has Flutter experience | None stated | Yes (same language as desktop) |
| Code reuse with desktop app | None either way (desktop is PySide6) | None | Chaquopy can embed some pure-Python logic (repos, SRS) but the UI would still be written separately |
| Chinese-text tappable words (§8.3) | Excellent: `RichText` + per-word `GestureRecognizer` is built for this | Fine (`Spannable` + `ClickableSpan`) | Poor with Kivy/BeeWare |
| MP3 playback with speed + seeking (§8.5) | `just_audio` package: rate, seek, positions — all supported | `MediaPlayer` / `ExoPlayer` (Media3) — supported | Weak/awkward |
| Local SQLite | `drift` (typesafe) or `sqflite` — same DB engine as desktop | Room | Chaquopy can run `sqlite3` |
| Reading sync bundle (zip + manifest) | `archive` + `crypto` packages — trivial | Fine | Trivial |
| Chinese-internet friendliness of toolchain | Good with mirrors (see §3) | Good with Aliyun Maven mirrors | pip mirrors needed |
| Build/deploy story | Single codebase; VS Code extension; hot reload | Android Studio/Gradle | Chaquopy ties app to Gradle anyway |

**Recommendation: Flutter.** The deciding factors are the user's existing Flutter experience, first-class support for tappable-word rich text and controllable audio playback (the two hardest review-screen requirements, §8.3/§8.5), and a straightforward mirror-based setup path on the Chinese internet. Python-on-Android options were rejected: they add toolchain complexity (Chaquopy still requires a full Android/Gradle setup) while delivering worse UI quality.

**Fallback:** if the Flutter toolchain proves unusable on the Chinese network even with mirrors, native Kotlin + Jetpack Compose is the fallback (same data model and sync-bundle spec; only the UI layer is rewritten). The sync bundle format and local schema in this plan are framework-agnostic on purpose.

## 2. Technology Stack (Flutter)

| Concern | Choice | Notes |
|---|---|---|
| Framework | Flutter (stable channel), Dart | User has prior experience |
| State management | `provider` (or `riverpod` if preferred) | Simple app; either is fine |
| Local DB | **`drift`** over SQLite | Type-safe queries; schema mirrors the desktop's review-relevant tables (§4) |
| Audio | **`just_audio`** + `just_audio_background` | play/pause, `setSpeed` (0.5×–2×), `seek` (±15s), position stream for UI |
| Archives / hashing | `archive`, `crypto` | Sync bundle unzip + SHA-256 manifest verification |
| File access | `file_picker`, `path_provider`, `share_plus` | Pick the sync bundle from USB/Downloads; app-local storage for DB + audio; share the results bundle out |
| Word tap rendering | `RichText` with per-word `TapGestureRecognizer` | Sentence-level translation toggles inline |
| Min Android version | Android 8.0 (API 26) | Covers essentially all modern devices; no lower requirement stated |

## 3. Development Environment Setup (fresh Linux + Chinese network)

Setup happens when Android implementation starts (roadmap step 6); recorded here so nothing is rediscovered later. All steps use **mainland-accessible mirrors** — no VPN assumed.

1. **JDK:** `sudo apt install openjdk-17-jdk` (distro repo).
2. **Android Studio:** download from `https://developer.android.google.cn/studio` (Google's China-accessible developer site) — provides SDK manager, emulator, and platform tools; accept licenses via SDK Manager.
3. **Android SDK pieces:** via Android Studio's SDK Manager (packages served from Google's China-reachable CDN). If any piece is slow, the SDK can also be fetched with the `commandline tools` + `sdkmanager` from the same site.
4. **Flutter SDK:** download the Linux tarball from **`https://mirrors.tuna.tsinghua.edu.cn/flutter/`** (or the official mirror `storage.flutter-io.cn`), extract to `~/flutter`, add to `PATH`.
5. **Flutter/Dart package mirrors** (add to shell profile):
   - `export PUB_HOSTED_URL=https://pub.flutter-io.cn`
   - `export FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn`
6. **Gradle & Maven mirrors** (in the Flutter project when created): point Gradle's distribution and repositories at **Aliyun/Tencent mirrors** —
   - `distributionUrl` from `https://mirrors.cloud.tencent.com/gradle/...`
   - repositories: `https://maven.aliyun.com/repository/google`, `.../repository/public`, `.../repository/gradle-plugin`
7. **VS Code extensions:** Flutter + Dart + Android iOS Emulator.
8. **Device:** enable Developer Options + USB debugging on the Android phone; connect via USB (`adb devices` to verify). A physical phone is the primary test target (no emulator dependency).
9. `flutter doctor` must be fully green before milestone A1.

*(For reference, the desktop-app environment on this laptop will similarly need the PyPI mirror: `pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple` — noted here so both setups are done once.)*

## 4. Data Layer

The Android app keeps a **read-mostly local copy** of the desktop data, plus its own pending results. Local schema (subset of desktop plan §3, same table/column names so `content.json` maps 1:1):

- `topics`, `lessons`, `sentences` (incl. segmentation JSON + translation), `words` (text, pinyin, definition, list_state — SRS fields received but not computed locally), `lesson_words`, `hsk_words` (needed only for word-popup status display).
- Local-only tables: `pending_reviews` (queued ratings + word-list actions taken on Android, with timestamps) and `sync_meta` (last import timestamp, bundle schema version).

**Import pipeline** (from `sync-v1.zip`, format per desktop plan §9):
1. User taps "Sync", picks the bundle (USB-transfer via file manager → Downloads, or any accessible path) — `file_picker`.
2. **Verify before applying:** read `manifest.json`, check schema version, recompute SHA-256 of `content.json` + every audio file; reject corrupt/partial bundles with a clear error (D-3).
3. **Backup:** copy the current local DB to `backups/pre-import-<ts>.db` before applying.
4. **Apply:** replace content tables inside one transaction; copy audio files into app storage; keep local `pending_reviews` (they're reconciled on the desktop, not dropped).
5. Report what changed (new lessons, updated words).

**Export (results) pipeline:**
1. Bundle `pending_reviews` into `events.jsonl`-style records + a `manifest.json` with checksums → `results-<timestamp>.zip` (same integrity scheme).
2. Offer "share/save" (`share_plus` / save to Downloads) so the user can copy it to the desktop over USB; desktop import side is already specified (desktop plan §9).

## 5. Screens (2 top-level destinations, per §12.2)

### 5.1 Home: Topics & Lessons
- Topic list → lesson list (in order) with **last reviewed** timestamps or "never reviewed" (§8.1).
- Prominent "Sync with desktop" action.

### 5.2 Lesson Review (§8.2–8.7)
- **Text view:** scrollable lesson text rendered sentence-by-sentence from stored segmentation; every word tappable (§8.3) → bottom sheet with word, pinyin, definition, list status, and the allowed actions (add to Basic/New, move Basic→New) — these queue to `pending_reviews` and apply locally immediately.
- **New-word highlighting:** first occurrence of each lesson new word styled (static, D-1).
- **Sentence translation toggle** (§8.4) per sentence.
- **Audio bar** (§8.5): `just_audio` — play/pause, restart, speed selector 0.5×–2.0×, −15s/+15s, "jump to end" → word review stage.
- **Word review stage** (§8.6): list of this lesson's Learned words, 4-way marking (difficult/easy/standard/unchanged, default standard), multi-select + select-all + bulk marking.
- **Completion** (§8.7): "mark complete" → writes local `pending_reviews` (reviewed events + `last_reviewed_at` locally) and offers next lesson / lesson list; **cancel** discards the session's rating changes (word-list actions already taken remain, same as desktop §8.7).
- **Offline by design:** everything needed is local after sync; no network calls at all in the Android app.

## 6. Rough Milestones

Deferred until the desktop app is in production (roadmap step 6). Order:

| # | Milestone | Contents |
|---|---|---|
| A0 | Environment | §3 setup on the laptop: JDK, Android Studio, Flutter SDK + mirrors, `flutter doctor` green, phone connected via USB |
| A1 | Scaffolding | Flutter project, drift schema, navigation shell, empty home screen runs on the physical phone |
| A2 | Sync import | bundle pick → verify → backup → apply → content visible in home/lesson lists |
| A3 | Review screen | text with tappable words, popups, sentence translations, new-word highlighting |
| A4 | Audio | audio bar (play/pause/restart/speed/±15s/jump-to-end) wired to synced MP3s |
| A5 | Word review + results export | rating UI, pending queue, results bundle creation + share |
| A6 | Test & deploy | round-trip with the real desktop app, install release APK on the phone |

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Chinese network blocks/throttles Flutter or Gradle downloads even with mirrors | Mirror list in §3 (Tsinghua/flutter-io.cn, Aliyun, Tencent); fallback to Kotlin+Compose (§1) as last resort |
| USB bundle copying is clunky | Bundles live in Downloads + `share_plus` for export; documented two-tap flow; format identical either way |
| Audio files make the app large | MP3s are short lessons (~1–2 min each); acceptable; storage in app-local dir |
| Drift schema drift vs desktop `content.json` | Bundle has `schema_version`; mismatch → clean reject with instruction to update the desktop app |

## 8. Open Points (non-blocking; decide at A1)

- State management: `provider` (default) vs `riverpod` — user's preference.
- Dark mode / font scaling: follow system defaults unless the user wants options.
- App name and launcher icon.


