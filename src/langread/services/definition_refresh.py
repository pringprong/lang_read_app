"""Refresh of all stored word definitions from the offline dictionary
(definitions plan §5, 2026-11-06).

For every word in the words table (and optionally every hsk_words entry):
dictionary hit → pinyin+definition overwritten with the dictionary values;
miss → the old (unreliable) definition is cleared so the gap is visible,
optionally re-filled by the translation model when `use_llm` is set.

The database is backed up before anything is written (same mechanism as
the sync import).
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from langread.db.connection import utcnow_iso
from langread.db.repositories import HskRepo, WordsRepo

ProgressFn = Callable[[str, int, int], None]


@dataclass(frozen=True)
class RefreshReport:
    """Outcome of one refresh run (or dry run)."""

    total_words: int = 0
    from_dictionary: int = 0
    from_llm: int = 0
    not_found: int = 0
    hsk_total: int = 0
    hsk_refreshed: int = 0
    misses: list[str] = field(default_factory=list)
    backup_path: Path | None = None
    dry_run: bool = False

    def summary(self) -> str:
        text = (
            f"{self.total_words} word(s): {self.from_dictionary} refreshed "
            f"from the dictionary, {self.from_llm} from the translation "
            f"model, {self.not_found} not found"
            + (" (cleared)" if not self.dry_run else "")
            + "."
        )
        if self.hsk_total:
            text += (
                f" HSK list: {self.hsk_refreshed} of {self.hsk_total} "
                "entries refreshed."
            )
        if self.backup_path is not None:
            text += f" Backup: {self.backup_path.name}"
        return text


class DefinitionRefreshService:
    def __init__(self, conn: sqlite3.Connection, dictionary,
                 llm=None, backups_dir: Path | None = None,
                 llm_delay: float = 1.0) -> None:
        self.conn = conn
        self.dictionary = dictionary
        self.llm = llm
        self.llm_delay = llm_delay  # pause between model calls (rate limit)
        self.words = WordsRepo(conn)
        self.hsk = HskRepo(conn)
        if backups_dir is None:
            from langread.app_config import backups_dir as default_backups_dir

            backups_dir = default_backups_dir()
        self._backups_dir = Path(backups_dir)
        if llm is not None:
            from langread.services.translation import TranslationService

            self._translation = TranslationService(conn, llm=llm)
        else:
            self._translation = None

    # ---- entry point ----

    def refresh(self, *, use_llm: bool = False, include_hsk: bool = False,
                dry_run: bool = False,
                progress: ProgressFn | None = None) -> RefreshReport:
        """Run the refresh; returns the report.

        use_llm — fill dictionary misses with the translation model
        (opt-in: by default misses are cleared, not invented).
        include_hsk — also refresh the hsk_words reference list.
        dry_run — report planned changes without writing anything.
        """
        rows = self.conn.execute("SELECT * FROM words ORDER BY id").fetchall()
        backup_path = None
        if not dry_run:
            backup_path = self._backup()

        misses: list[str] = []
        from_dictionary = from_llm = not_found = 0

        for i, row in enumerate(rows):
            if progress:
                progress("words", i + 1, len(rows))
            entry = self.dictionary.lookup(row["text"]) if self.dictionary else None
            if entry is not None and (entry.pinyin or entry.definition):
                from_dictionary += 1
                if not dry_run:
                    self.words.set_translation(
                        row["id"], entry.pinyin or row["pinyin"],
                        entry.definition or row["definition"],
                        definition_source=(
                            "dictionary" if entry.definition else None
                        ),
                    )
                continue
            # dictionary miss → translation model (opt-in) or clear
            filled = False
            if use_llm and self._translation is not None:
                pinyin, definition = self._translation.translate_word(row["text"])
                time.sleep(self.llm_delay)
                if pinyin or definition:
                    from_llm += 1
                    filled = True
                    if not dry_run:
                        self.words.set_translation(
                            row["id"], pinyin or row["pinyin"], definition,
                            definition_source=(
                                "llm" if definition is not None else None
                            ),
                        )
            if not filled:
                not_found += 1
                misses.append(row["text"])
                if not dry_run:
                    # old definition was unreliable → clear it, keep pinyin
                    self.words.set_translation(
                        row["id"], row["pinyin"], None, definition_source=None
                    )

        hsk_total = hsk_refreshed = 0
        if include_hsk:
            hsk_rows = self.conn.execute(
                "SELECT * FROM hsk_words ORDER BY id"
            ).fetchall()
            hsk_total = len(hsk_rows)
            for i, row in enumerate(hsk_rows):
                if progress:
                    progress("HSK words", i + 1, hsk_total)
                entry = (
                    self.dictionary.lookup(row["text"]) if self.dictionary else None
                )
                if entry is not None and (entry.pinyin or entry.definition):
                    hsk_refreshed += 1
                    if not dry_run:
                        self.hsk.set_translation(
                            row["id"], entry.pinyin or row["pinyin"],
                            entry.definition or row["definition"],
                        )

        return RefreshReport(
            total_words=len(rows), from_dictionary=from_dictionary,
            from_llm=from_llm, not_found=not_found,
            hsk_total=hsk_total, hsk_refreshed=hsk_refreshed,
            misses=misses, backup_path=backup_path, dry_run=dry_run,
        )

    # ---- helpers ----

    def _backup(self) -> Path:
        """Copy the database to backups/pre-refresh-<timestamp>.db."""
        self._backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = utcnow_iso().replace(":", "")
        backup_path = self._backups_dir / f"pre-refresh-{stamp}.db"
        with sqlite3.connect(backup_path) as destination:
            self.conn.backup(destination)
        return backup_path
