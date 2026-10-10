from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import sqlite3


class ResponseCache:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=30)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS explorer_response(
                 source TEXT NOT NULL,
                 position_key TEXT NOT NULL,
                 filter_key TEXT NOT NULL,
                 fetched_at TEXT NOT NULL,
                 endpoint TEXT NOT NULL,
                 response_json TEXT NOT NULL,
                 PRIMARY KEY(source, position_key, filter_key)
               ) WITHOUT ROWID"""
        )
        self.db.commit()

    def get(self, source: str, position_key: str, filter_key: str) -> dict | None:
        row = self.db.execute(
            "SELECT fetched_at,endpoint,response_json FROM explorer_response WHERE source=? AND position_key=? AND filter_key=?",
            (source, position_key, filter_key),
        ).fetchone()
        if not row:
            return None
        return {"fetched_at": row[0], "endpoint": row[1], "payload": json.loads(row[2])}

    def put(self, source: str, position_key: str, filter_key: str, endpoint: str, payload: dict) -> str:
        fetched = dt.datetime.now(dt.timezone.utc).isoformat()
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO explorer_response VALUES(?,?,?,?,?,?)",
                (source, position_key, filter_key, fetched, endpoint, json.dumps(payload, separators=(",", ":"))),
            )
        return fetched

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "ResponseCache":
        return self

    def __exit__(self, *_args) -> None:
        self.close()
