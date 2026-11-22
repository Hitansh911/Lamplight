"""Local-only storage. Everything lives in one SQLite file on this machine."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL,
    mood       INTEGER NOT NULL,
    text       TEXT    NOT NULL,
    reply      TEXT    NOT NULL DEFAULT '',
    level      INTEGER NOT NULL DEFAULT 0,
    themes     TEXT    NOT NULL DEFAULT '[]',
    source     TEXT    NOT NULL DEFAULT 'offline'
);
CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created_at);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

MOOD_NAMES = {1: "Heavy", 2: "Low", 3: "Okay", 4: "Good", 5: "Bright"}


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # -- entries -----------------------------------------------------------
    def add_entry(
        self,
        text: str,
        mood: int,
        reply: str,
        level: int,
        themes: list[str],
        source: str,
        created_at: datetime | None = None,
    ) -> int:
        stamp = (created_at or datetime.now()).isoformat(timespec="seconds")
        with closing(self._conn()) as c, c:
            cur = c.execute(
                "INSERT INTO entries (created_at, mood, text, reply, level, themes, source)"
                " VALUES (?,?,?,?,?,?,?)",
                (stamp, int(mood), text, reply, int(level), json.dumps(themes), source),
            )
            return int(cur.lastrowid)

    def entries(self, limit: int | None = None, search: str | None = None) -> list[dict]:
        sql = "SELECT * FROM entries"
        args: list = []
        if search:
            sql += " WHERE text LIKE ? ESCAPE '\\'"
            esc = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            args.append(f"%{esc}%")
        sql += " ORDER BY created_at DESC, id DESC"
        if limit:
            sql += " LIMIT ?"
            args.append(int(limit))
        with closing(self._conn()) as c:
            rows = c.execute(sql, args).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["themes"] = json.loads(d["themes"] or "[]")
            out.append(d)
        return out

    def count(self) -> int:
        with closing(self._conn()) as c:
            return int(c.execute("SELECT COUNT(*) FROM entries").fetchone()[0])

    def delete_entry(self, entry_id: int) -> None:
        with closing(self._conn()) as c, c:
            c.execute("DELETE FROM entries WHERE id = ?", (int(entry_id),))

    def delete_all(self) -> None:
        with closing(self._conn()) as c, c:
            c.execute("DELETE FROM entries")

    # -- settings ----------------------------------------------------------
    def get_setting(self, key: str, default: str = "") -> str:
        with closing(self._conn()) as c:
            row = c.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with closing(self._conn()) as c, c:
            c.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    # -- export ------------------------------------------------------------
    def export_json(self) -> str:
        return json.dumps(self.entries(), indent=2, ensure_ascii=False)

    def export_markdown(self) -> str:
        parts = ["# My Lamplight journal\n"]
        for e in reversed(self.entries()):
            dt = datetime.fromisoformat(e["created_at"])
            parts.append(
                f"## {dt:%A, %d %B %Y, %H:%M} (mood: {MOOD_NAMES.get(e['mood'], e['mood'])})\n\n"
                f"{e['text']}\n\n> {e['reply']}\n"
            )
        return "\n".join(parts)
