"""Ingest: scrape 1 manga lalu upsert ke DB (idempoten by slug/url)."""
from __future__ import annotations
import re
from sqlalchemy import select
from db import SessionLocal, Manga, Genre, Chapter, init_db
from scraper import scrape_detail


def _chapter_number(name: str) -> float | None:
    m = re.search(r"([\d]+(?:\.[\d]+)?)", name or "")
    return float(m.group(1)) if m else None


def is_detailed(slug: str | None = None, url: str | None = None) -> bool:
    """True kalau manga (by slug ATAU source_url) sudah pernah di-scrape detail.

    Penanda "sudah detail" = synopsis terisi (crawl katalog tak isi synopsis).
    Dipakai untuk skip re-scraping saat judul/URL sama muncul lagi (mis. di
    page 1 dan page 2, atau saat menjalankan ulang scraper).
    """
    if not slug and not url:
        return False
    with SessionLocal() as s:
        stmt = select(Manga.synopsis)
        if slug:
            stmt = stmt.where(Manga.slug == slug)
        else:
            stmt = stmt.where(Manga.source_url == url)
        syn = s.scalar(stmt)
        return syn is not None and syn != ""


def _get_or_create_genre(session, name: str) -> Genre:
    g = session.scalar(select(Genre).where(Genre.name == name))
    if not g:
        g = Genre(name=name)
        session.add(g)
        session.flush()
    return g


def upsert_manga(data: dict) -> int:
    """Terima output scrape_detail(), simpan/update. Return manga.id."""
    with SessionLocal() as session:
        m = session.scalar(select(Manga).where(Manga.slug == data["slug"]))
        if not m:
            m = Manga(slug=data["slug"])
            session.add(m)

        # field skalar
        for f in ("title", "title_alt", "type", "theme", "author", "status",
                  "age_rating", "reading_direction", "total_views",
                  "synopsis", "thumbnail", "source_url"):
            setattr(m, f, data.get(f))

        # genres (m2m)
        m.genres = [_get_or_create_genre(session, g) for g in data.get("genres", [])]

        # chapters (upsert by url); dedup url ganda dalam 1 halaman
        existing = {c.url: c for c in m.chapters}
        seen: set[str] = set()
        for ch in data.get("chapters", []):
            if ch["url"] in seen:
                continue
            seen.add(ch["url"])
            row = existing.get(ch["url"])
            if row:
                row.name = ch["name"]
                row.released_at = ch["released_at"]
                row.number = _chapter_number(ch["name"])
            else:
                m.chapters.append(Chapter(
                    name=ch["name"],
                    number=_chapter_number(ch["name"]),
                    url=ch["url"],
                    released_at=ch["released_at"],
                ))

        session.commit()
        return m.id


def ingest_url(url: str) -> int:
    return upsert_manga(scrape_detail(url))


def upsert_card(card: dict) -> tuple[int, bool]:
    """Simpan data level-kartu dari halaman katalog (tanpa detail penuh).

    Idempoten by slug. Tidak menimpa field detail yang sudah terisi
    (author/synopsis/genres/chapters) — hanya isi kalau baris baru.
    Return (manga_id, is_new).
    """
    with SessionLocal() as session:
        m = session.scalar(select(Manga).where(Manga.slug == card["slug"]))
        is_new = m is None
        if is_new:
            m = Manga(slug=card["slug"])
            session.add(m)
        # selalu segarkan field kartu
        m.title = card["title"]
        m.source_url = card["url"]
        if card.get("card_thumbnail"):
            m.thumbnail = card["card_thumbnail"]
        if card.get("card_type"):
            m.type = card["card_type"]
        if card.get("card_status"):
            m.status = card["card_status"]
        session.commit()
        return m.id, is_new


if __name__ == "__main__":
    import sys
    init_db()
    url = sys.argv[1] if len(sys.argv) > 1 else "https://komiku.org/manga/50kg-cinderella/"
    mid = ingest_url(url)
    print(f"OK ingested manga id={mid} from {url}")
