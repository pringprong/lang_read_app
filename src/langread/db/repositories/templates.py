"""Repository for prompt templates (requirements §4.5, §7.5).

Templates are stored in the database (user-editable in-app) and seeded from
the bundled JSON resource on first use.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from langread.db.connection import transaction, utcnow_iso

DEFAULT_TEMPLATES_FILE = (
    Path(__file__).parents[2] / "resources" / "prompts" / "default_templates.json"
)


class TemplatesRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def seed_defaults(self, force: bool = False) -> int:
        """Insert bundled default templates that are missing. Returns count added."""
        defaults = json.loads(DEFAULT_TEMPLATES_FILE.read_text(encoding="utf-8"))
        added = 0
        with transaction(self.conn):
            for name, template in defaults.items():
                if force:
                    self.conn.execute(
                        "INSERT INTO prompt_templates (name, template, updated_at) "
                        "VALUES (?, ?, ?) "
                        "ON CONFLICT(name) DO UPDATE SET template = excluded.template, "
                        "updated_at = excluded.updated_at",
                        (name, template, utcnow_iso()),
                    )
                    added += 1
                else:
                    cur = self.conn.execute(
                        "INSERT OR IGNORE INTO prompt_templates "
                        "(name, template, updated_at) VALUES (?, ?, ?)",
                        (name, template, utcnow_iso()),
                    )
                    added += cur.rowcount
        return added

    def get(self, name: str) -> str | None:
        row = self.conn.execute(
            "SELECT template FROM prompt_templates WHERE name = ?", (name,)
        ).fetchone()
        return row["template"] if row else None

    def upsert(self, name: str, template: str) -> None:
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO prompt_templates (name, template, updated_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET template = excluded.template, "
                "updated_at = excluded.updated_at",
                (name, template, utcnow_iso()),
            )

    def list_names(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT name FROM prompt_templates ORDER BY name"
        ).fetchall()
        return [r["name"] for r in rows]
