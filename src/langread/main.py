"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from langread.ui.main_menu import MainMenu


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LangRead")
    app.setOrganizationName("LangReadApp")
    window = MainMenu()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
