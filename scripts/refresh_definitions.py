"""Refresh every stored word definition from the offline dictionary.

Usage:
    .venv/bin/python scripts/refresh_definitions.py --dry-run
    .venv/bin/python scripts/refresh_definitions.py
    .venv/bin/python scripts/refresh_definitions.py --with-llm --include-hsk

Options:
    --dry-run     report the planned changes without writing anything
    --with-llm    for words not in the dictionary, ask the configured
                  translation model (off by default: misses are cleared,
                  not invented)
    --include-hsk also refresh the bundled HSK reference list definitions

The database is backed up (backups/pre-refresh-<ts>.db) before any write.
Honors LANGREAD_DATA_DIR and LANGREAD_CEDICT like the app itself.
"""

from __future__ import annotations

import argparse
import sys

from langread.app_config import db_path
from langread.db import connect
from langread.db.repositories import SettingsRepo
from langread.services.dictionary import get_dictionary
from langread.services.definition_refresh import DefinitionRefreshService
from langread.services.model_settings import ModelSettings, ModelSettingsError

MAX_MISSES_SHOWN = 30


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh word definitions from the offline dictionary."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="report planned changes only")
    parser.add_argument("--with-llm", action="store_true",
                        help="fill dictionary misses with the translation model")
    parser.add_argument("--include-hsk", action="store_true",
                        help="also refresh HSK list definitions")
    args = parser.parse_args()

    dictionary = get_dictionary()
    if dictionary is None:
        print("Offline dictionary unavailable "
              "(missing resource or LANGREAD_CEDICT=off).")
        return 1

    llm = None
    if args.with_llm:
        conn_for_settings = connect(db_path())
        try:
            from langread.services.llm_client import LlmClient

            llm = LlmClient(
                ModelSettings(SettingsRepo(conn_for_settings)).llm_config("trans")
            )
        except ModelSettingsError as exc:
            print(f"Translation model not configured: {exc}")
            print("Run without --with-llm, or configure it in Model settings.")
            return 1
        finally:
            conn_for_settings.close()

    conn = connect(db_path())
    try:
        service = DefinitionRefreshService(conn, dictionary, llm=llm)
        report = service.refresh(
            use_llm=args.with_llm,
            include_hsk=args.include_hsk,
            dry_run=args.dry_run,
            progress=lambda stage, current, total: print(
                f"\r{stage}: {current}/{total}", end="", flush=True
            ),
        )
        print("\n")
        print("DRY RUN — nothing was changed." if report.dry_run else "Done.")
        print(report.summary())
        if report.misses:
            shown = report.misses[:MAX_MISSES_SHOWN]
            more = len(report.misses) - len(shown)
            print(f"Not in the dictionary: {', '.join(shown)}"
                  + (f" … (+{more} more)" if more > 0 else ""))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
