-- ============================================================
-- Otakudesu DB schema  (SQLite dialect; catatan Postgres di bawah)
-- ------------------------------------------------------------
-- Desain:
--   * anime             : 1 baris per anime (field skalar)
--   * genre + anime_genre : many-to-many (1 anime banyak genre)
--   * episode           : 1 baris per episode (1 anime banyak episode)
--
-- Skema ini cuma REFERENSI; DB sebenarnya dibuat oleh db.init_db()
-- (SQLAlchemy). Kalau berbeda, db.py yang jadi acuan.
-- ============================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS anime (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT    NOT NULL UNIQUE,          -- 100-man-no-inochi-sub-indo
    title           TEXT    NOT NULL,
    title_japanese  TEXT,                             -- judul Jepang (kanji)
    type            TEXT,                             -- TV / Movie / OVA / ONA
    status          TEXT,                             -- Ongoing / Completed
    score           REAL,                             -- skor (cth 6.48)
    producers       TEXT,                             -- daftar produser (dipisah koma)
    studio          TEXT,
    total_episode   TEXT,                             -- string ("12", "?")
    duration        TEXT,                             -- "23 Menit"
    release_date    TEXT,                             -- "Oct 2, 2020"
    synopsis        TEXT,
    thumbnail       TEXT,
    source_url      TEXT    NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_anime_status ON anime(status);
CREATE INDEX IF NOT EXISTS idx_anime_type   ON anime(type);

CREATE TABLE IF NOT EXISTS genre (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS anime_genre (
    anime_id INTEGER NOT NULL REFERENCES anime(id) ON DELETE CASCADE,
    genre_id INTEGER NOT NULL REFERENCES genre(id) ON DELETE CASCADE,
    PRIMARY KEY (anime_id, genre_id)
);

CREATE TABLE IF NOT EXISTS episode (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    anime_id    INTEGER NOT NULL REFERENCES anime(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,                       -- "... Episode 12 (End) ..."
    number      REAL,                                   -- 12, 7.5 (utk sorting)
    url         TEXT    NOT NULL UNIQUE,
    released_at TEXT,                                    -- string tanggal "9 Januari,2021"
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_episode_anime ON episode(anime_id, number);

-- Link download episode tidak punya tabel: endpoint di API live-fetch ke
-- Otakudesu tiap request (parse blok .download), jadi tidak disimpan di sini.

-- ============================================================
-- Catatan Postgres (kalau pindah dari SQLite):
--   INTEGER PRIMARY KEY AUTOINCREMENT  ->  BIGSERIAL PRIMARY KEY
--   REAL                               ->  NUMERIC(8,2)
--   TEXT DEFAULT (datetime('now'))     ->  TIMESTAMPTZ DEFAULT now()
--   PRAGMA foreign_keys = ON;          ->  (tidak perlu)
-- ============================================================
