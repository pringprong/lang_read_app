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

- [ ] (pending)
