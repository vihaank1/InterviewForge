"""SQLite storage. Every request opens a short-lived connection; WAL supports local use."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  role TEXT NOT NULL,
  track TEXT NOT NULL,
  difficulty TEXT NOT NULL,
  current_question TEXT NOT NULL,
  current_focus TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  version INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rounds (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  focus TEXT NOT NULL,
  score REAL NOT NULL,
  evaluation_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS rounds_by_session ON rounds(session_id, id);
CREATE TABLE IF NOT EXISTS designs (
  id TEXT PRIMARY KEY,
  prompt TEXT NOT NULL,
  candidate_design TEXT,
  architecture_json TEXT NOT NULL,
  review_json TEXT,
  score REAL,
  hints_json TEXT,
  created_at TEXT NOT NULL
);
"""

class Database:
    def __init__(self, path: str):
        self.path = str(Path(path).expanduser().resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA busy_timeout = 15000')
        conn.execute('PRAGMA journal_mode = WAL')
        return conn
