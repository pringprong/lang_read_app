# Smoke Checklist (per milestone)

Manual checks run after each milestone's automated tests pass.
Environment note: tests run with `QT_QPA_PLATFORM=offscreen` when there is no
display; the app itself runs on the real desktop session.

## M0 — Scaffolding

- [x] `pytest` passes (app config paths, main-menu construction).
- [x] `langread` command (console script) launches the main-menu window.
- [x] Window shows the 8 menu options from requirements §12.1.
- [x] Clicking any option shows the "not implemented yet" dialog.
- [x] Data directory is created at `~/.local/share/LangReadApp` on Linux.
- [x] `LANGREAD_DATA_DIR` override works (used by tests).

## M1 — Data layer

- [ ] (pending)
