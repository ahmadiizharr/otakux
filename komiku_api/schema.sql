-- ============================================================
-- Komiku DB schema  (SQLite dialect; catatan Postgres di bawah)
-- ------------------------------------------------------------
-- Desain:
--   * manga            : 1 baris per komik (field skalar)
--   * genre + manga_genre : many-to-many (1 manga banyak genre)
--   * chapter          : 1 baris per chapter (1 manga banyak chapter)
--
-- "tema" (theme) & "tipe" (type) disimpan sebagai kolom di manga
-- karena pada Komiku umumnya bernilai tunggal. Kalau nanti mau
-- multi-tema, tinggal jadikan m2m seperti genre.
-- ============================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS manga (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    slug              TEXT    NOT NULL UNIQUE,          -- 50kg-cinderella
    title             TEXT    NOT NULL,
    title_alt         TEXT,
    type              TEXT,                             -- Manga / Manhwa / Manhua
    theme             TEXT,                             -- Tema (cth: Drama)
    author            TEXT,
    status            TEXT,                             -- Ongoing / End
    age_rating        TEXT,                             -- content rating, cth "15+"
    reading_direction TEXT,                             -- "Kanan ke kiri"
    total_views       INTEGER DEFAULT 0,
    synopsis          TEXT,
    thumbnail         TEXT,
    source_url        TEXT    NOT NULL,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_manga_status ON manga(status);
CREATE INDEX IF NOT EXISTS idx_manga_type   ON manga(type);

CREATE TABLE IF NOT EXISTS genre (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS manga_genre (
    manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
    genre_id INTEGER NOT NULL REFERENCES genre(id) ON DELETE CASCADE,
    PRIMARY KEY (manga_id, genre_id)
);

CREATE TABLE IF NOT EXISTS chapter (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    manga_id    INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,                       -- "Chapter 8"
    number      REAL,                                   -- 8, 2.2, 1.1 (utk sorting)
    url         TEXT    NOT NULL UNIQUE,
    released_at TEXT,                                    -- string tanggal asli "07/09/2022"
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chapter_manga ON chapter(manga_id, number);

-- Gambar halaman tidak punya tabel: reader di API live-fetch ke Komiku
-- tiap request (parse #Baca_Komik img.ww), jadi tidak ada URL gambar yang
-- disimpan di sini.

-- ============================================================
-- Catatan Postgres (kalau pindah dari SQLite):
--   INTEGER PRIMARY KEY AUTOINCREMENT  ->  BIGSERIAL PRIMARY KEY
--   REAL                               ->  NUMERIC(8,2)
--   TEXT DEFAULT (datetime('now'))     ->  TIMESTAMPTZ DEFAULT now()
--   PRAGMA foreign_keys = ON;          ->  (tidak perlu)
-- ============================================================
