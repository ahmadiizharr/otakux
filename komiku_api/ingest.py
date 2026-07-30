"""Ingest: scrape 1 anime lalu upsert ke DB (idempoten by slug/url episode)."""
from __future__ import annotations
from sqlalchemy import select
from db import SessionLocal, Anime, Genre, Episode
from scraper import scrape_detail


def is_detailed(slug: str | None = None, url: str | None = None) -> bool:
    """True kalau anime (by slug ATAU source_url) sudah pernah di-scrape detail.

    Penanda "sudah detail" = synopsis terisi (crawl katalog tak isi synopsis).
    Dipakai untuk skip re-scraping saat judul/URL sama muncul lagi.
    """
    if not slug and not url:
        return False
    with SessionLocal() as s:
        stmt = select(Anime.synopsis)
        if slug:
            stmt = stmt.where(Anime.slug == slug)
        else:
            stmt = stmt.where(Anime.source_url == url)
        syn = s.scalar(stmt)
        return syn is not None and syn != ""


def _get_or_create_genre(session, name: str) -> Genre:
    g = session.scalar(select(Genre).where(Genre.name == name))
    if not g:
        g = Genre(name=name)
        session.add(g)
        session.flush()
    return g


def upsert_anime(data: dict) -> int:
    """Terima output scrape_detail(), simpan/update. Return anime.id."""
    with SessionLocal() as session:
        m = session.scalar(select(Anime).where(Anime.slug == data["slug"]))
        if not m:
            m = Anime(slug=data["slug"])
            session.add(m)

        # field skalar (thumbnail SENGAJA tidak di sini — dimiliki AniList)
        for f in ("title", "title_japanese", "type", "status", "score",
                  "producers", "studio", "total_episode", "duration",
                  "release_date", "synopsis", "source_url"):
            setattr(m, f, data.get(f))

        # thumbnail: sumber utama = AniList (lihat fetch_thumbnails.py). Jangan
        # timpa yang sudah ada; thumbnail Otakudesu cuma cadangan kalau kosong.
        if not m.thumbnail and data.get("thumbnail"):
            m.thumbnail = data["thumbnail"]

        # genres (m2m)
        m.genres = [_get_or_create_genre(session, g) for g in data.get("genres", [])]

        # episodes (upsert by url); dedup url ganda dalam 1 halaman
        existing = {e.url: e for e in m.episodes}
        seen: set[str] = set()
        for ep in data.get("episodes", []):
            if ep["url"] in seen:
                continue
            seen.add(ep["url"])
            row = existing.get(ep["url"])
            if row:
                row.name = ep["name"]
                row.number = ep["number"]
                row.released_at = ep["released_at"]
            else:
                m.episodes.append(Episode(
                    name=ep["name"],
                    number=ep["number"],
                    url=ep["url"],
                    released_at=ep["released_at"],
                ))

        session.commit()
        return m.id


def ingest_url(url: str) -> int:
    return upsert_anime(scrape_detail(url))


def upsert_card(card: dict) -> tuple[int, bool]:
    """Simpan data level-kartu dari halaman katalog (tanpa detail penuh).

    Idempoten by slug. Tidak menimpa field detail yang sudah terisi
    (synopsis/genres/episodes) — hanya isi field kartu. Return (anime_id, is_new).
    """
    with SessionLocal() as session:
        m = session.scalar(select(Anime).where(Anime.slug == card["slug"]))
        is_new = m is None
        if is_new:
            m = Anime(slug=card["slug"])
            session.add(m)
        # selalu segarkan field kartu
        m.title = card["title"]
        m.source_url = card["url"]
        # thumbnail: jangan timpa (AniList utama; kartu cuma cadangan bila kosong)
        if not m.thumbnail and card.get("card_thumbnail"):
            m.thumbnail = card["card_thumbnail"]
        session.commit()
        return m.id, is_new


if __name__ == "__main__":
    import sys
    from db import init_db
    init_db()
    url = sys.argv[1] if len(sys.argv) > 1 else \
        "https://otakudesu.blog/anime/100-man-no-inochi-sub-indo/"
    mid = ingest_url(url)
    print(f"OK ingested anime id={mid} from {url}")
