"""Repository for app settings (requirements §4.5) — JSON key/value store."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from langread.db.connection import transaction


class SettingsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return json.loads(row["value"])

    def set(self, key: str, value: Any) -> None:
        encoded = json.dumps(value, ensure_ascii=False)
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, encoded),
            )

    def delete(self, key: str) -> None:
        with transaction(self.conn):
            self.conn.execute("DELETE FROM settings WHERE key = ?", (key,))

    def keys(self) -> list[str]:
        rows = self.conn.execute("SELECT key FROM settings ORDER BY key").fetchall()
        return [r["key"] for r in rows]
