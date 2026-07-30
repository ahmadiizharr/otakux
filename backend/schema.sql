CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    attachment_key TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
