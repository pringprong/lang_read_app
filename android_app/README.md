# LangRead (Android)

Review-only companion app for the LangRead desktop app — **both apps live in
this repository** (the Flutter project is in `android_app/`, the desktop
Python app in `src/langread/`). See
`../20261107_android_app_detailed_plan.md` for the full detailed plan.

**Scope:** select a topic → review a lesson (tappable words, translations,
audio, word ratings), and sync content/results with the desktop over USB.
Everything works offline after content is imported. No authoring, no model
configuration — that's the desktop's job.

## Project layout

- `lib/data/` — drift database (schema mirrors the desktop), bundle
  verification/import/export (§3/§4 of the plan)
- `lib/domain/` — segmentation → tappable-token logic
- `lib/services/` — `just_audio` wrapper for the audio bar (§8.5)
- `lib/state/` — review session semantics (§8.7 complete/cancel), sync state
- `lib/screens/` — Home (topics→lessons), Review, Sync tabs
- `test/` — unit/widget tests + cross-app round-trip tests
- `tool/` — Python scripts that talk to the **real desktop code**:
  - `make_fixture.py` — regenerates `test/fixtures/sync-v1.zip` via the
    desktop `SyncService` (run after changing the desktop sync format!)
  - `verify_results_bundle.py` — imports an Android results bundle into a
    fresh desktop DB and asserts every event landed (the round-trip check)

## Everyday commands

```bash
# tests + lint (host, no device needed)
flutter analyze && flutter test

# regen the desktop fixture (needs the desktop repo + venv)
/home/pringprong/lang_read_app/.venv/bin/python tool/make_fixture.py

# cross-app round-trip check
flutter test test/roundtrip_bundle_test.dart
/home/pringprong/lang_read_app/.venv/bin/python \
    tool/verify_results_bundle.py build/results-roundtrip.zip

# build the sideload release APK (plan §9)
flutter build apk --release
# → build/app/outputs/flutter-apk/app-release.apk
# copy it to the phone, tap it, allow "install unknown apps", install.
```

Signing: the release keystore is `~/keystores/langread-release.jks`
(alias `langread`, PKCS12); its password is in
`~/keystores/langread-release.password` (chmod 600).
`android/key.properties` (gitignored) points Gradle at it.
**Losing the keystore means future APKs can't install over this one.**

## Sync flow (D-3)

1. Desktop: Sync → export bundle → copy `sync-v1.zip` to the phone
   (e.g. Downloads).
2. Phone: Sync tab → *Import from desktop* → pick the zip (verified +
   backed up before anything is applied; pending results are kept).
3. Review lessons on the phone; ratings and word-list actions queue
   offline in `pending_events`.
4. Phone: Sync tab → *Export results* → share/save `results-*.zip`.
5. Desktop: Sync → import results (most-recent rating wins).

The app's documents directory (visible over USB) holds `langread.db`,
`audio/`, `backups/` (pre-import, last 5), and `exports/`.
