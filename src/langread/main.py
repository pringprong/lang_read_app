"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from langread.ui.main_menu import MainMenu


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LangRead")
    app.setOrganizationName("LangReadApp")
    window = MainMenu()
    window.show()
    smoke_ok = True
    if "--smoke-test" in sys.argv:
        # used to verify packaged builds: boot, show, load resources, exit
        try:
            from langread.db.repositories import TemplatesRepo
            from langread.services.hsk import HskService

            conn = window.conn()  # opens the DB and applies the schema
            TemplatesRepo(conn).seed_defaults()
            hsk_rows = HskService(conn).import_if_needed()
            print(f"smoke: schema OK, templates seeded, "
                  f"HSK imported={hsk_rows}", flush=True)
        except Exception as exc:  # noqa: BLE001 - reported via exit code
            smoke_ok = False
            print(f"smoke FAILED: {exc}", flush=True)
        QTimer.singleShot(1500, app.quit)
    rc = app.exec()
    return rc if smoke_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
