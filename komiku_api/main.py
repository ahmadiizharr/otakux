"""
Otakudesu API  —  REST API katalog anime hasil scraping.

Jalankan:
    uvicorn main:app --reload
Docs interaktif:
    http://127.0.0.1:8000/docs
"""
from __future__ import annotations
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from fastapi import (
    FastAPI, Depends, HTTPException, Query, BackgroundTasks,
)
from pydantic import BaseModel
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session

from db import SessionLocal, Anime, Genre, Episode, init_db
from ingest import ingest_url
from scraper import (
    scrape_episode, resolve_link, resolve_mirror_streams, HttpError, BASE,
)

app = FastAPI(title="Otakudesu API", version="0.1.0",
              description="REST API katalog anime hasil scraping Otakudesu.")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def _startup():
    init_db()


# ---------- Pydantic response schemas ----------
class EpisodeOut(BaseModel):
    name: str
    number: Optional[float] = None
    url: str
    released_at: Optional[str] = None

    class Config:
        from_attributes = True


class AnimeListItem(BaseModel):
    slug: str
    title: str
    type: Optional[str] = None
    status: Optional[str] = None
    score: Optional[float] = None
    thumbnail: Optional[str] = None

    class Config:
        from_attributes = True


class AnimeDetail(BaseModel):
    slug: str
    title: str
    title_japanese: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    score: Optional[float] = None
    producers: Optional[str] = None
    studio: Optional[str] = None
    total_episode: Optional[str] = None
    duration: Optional[str] = None
    release_date: Optional[str] = None
    synopsis: Optional[str] = None
    thumbnail: Optional[str] = None
    source_url: str
    genres: list[str] = []
    episodes: list[EpisodeOut] = []

    class Config:
        from_attributes = True


def _detail(m: Anime) -> AnimeDetail:
    return AnimeDetail(
        slug=m.slug, title=m.title, title_japanese=m.title_japanese,
        type=m.type, status=m.status, score=m.score, producers=m.producers,
        studio=m.studio, total_episode=m.total_episode, duration=m.duration,
        release_date=m.release_date, synopsis=m.synopsis, thumbnail=m.thumbnail,
        source_url=m.source_url,
        genres=[g.name for g in m.genres],
        episodes=[EpisodeOut.model_validate(e) for e in m.episodes],
    )


# ---------- Endpoints ----------
@app.get("/anime", response_model=list[AnimeListItem])
def list_anime(
    q: Optional[str] = Query(None, description="cari di judul"),
    genre: Optional[str] = Query(None, description="nama genre (mis. Action)"),
    status: Optional[str] = Query(None, description="Ongoing / Completed / Drop"),
    type: Optional[str] = Query(None, description="TV / Movie / OVA / ONA / Special"),
    skip: int = 0,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    # Filter status/type/genre case-insensitive supaya 'ongoing' == 'Ongoing'.
    stmt = select(Anime)
    if q:
        stmt = stmt.where(Anime.title.ilike(f"%{q}%"))
    if status:
        stmt = stmt.where(func.lower(Anime.status) == status.lower())
    if type:
        stmt = stmt.where(func.lower(Anime.type) == type.lower())
    if genre:
        stmt = stmt.join(Anime.genres).where(func.lower(Genre.name) == genre.lower())
    stmt = stmt.order_by(Anime.updated_at.desc()).offset(skip).limit(limit)
    return db.scalars(stmt).unique().all()


@app.get("/anime/{slug}", response_model=AnimeDetail)
def get_anime(slug: str, db: Session = Depends(get_db)):
    m = db.scalar(select(Anime).where(Anime.slug == slug))
    if not m:
        raise HTTPException(404, "Anime tidak ditemukan")
    return _detail(m)


@app.get("/anime/{slug}/episodes", response_model=list[EpisodeOut])
def get_episodes(slug: str, db: Session = Depends(get_db)):
    m = db.scalar(select(Anime).where(Anime.slug == slug))
    if not m:
        raise HTTPException(404, "Anime tidak ditemukan")
    return sorted(m.episodes, key=lambda e: (e.number or 0))


@app.get("/updates")
def latest_updates(
    skip: int = 0,
    limit: int = Query(24, le=60),
    db: Session = Depends(get_db),
):
    """Anime yang paling baru update episode, diurutkan dari kapan episode
    terakhir masuk DB (created_at, di-set saat scrape) — bukan judul populer."""
    rows = db.execute(text("""
        WITH latest AS (
            SELECT anime_id, MAX(created_at) AS mc
            FROM episode
            GROUP BY anime_id
        )
        SELECT a.id, a.slug, a.title, a.type, a.status, a.score, a.thumbnail,
               latest.mc AS mc
        FROM latest JOIN anime a ON a.id = latest.anime_id
        ORDER BY latest.mc DESC
        LIMIT :limit OFFSET :skip
    """), {"limit": limit, "skip": skip}).all()

    out = []
    for r in rows:
        eps = db.execute(text("""
            SELECT name, number, released_at
            FROM episode
            WHERE anime_id = :aid
            ORDER BY created_at DESC, number DESC
            LIMIT 3
        """), {"aid": r.id}).all()
        out.append({
            "slug": r.slug, "title": r.title, "type": r.type,
            "status": r.status, "score": r.score, "thumbnail": r.thumbnail,
            "latest_episodes": [
                {"name": e.name, "number": e.number, "released_at": e.released_at}
                for e in eps
            ],
        })
    return out


@app.get("/slugs")
def all_slugs(db: Session = Depends(get_db)):
    """Semua slug + updated_at (buat sitemap SEO). Satu query, ringan."""
    rows = db.execute(text(
        "SELECT slug, updated_at FROM anime ORDER BY updated_at DESC"
    )).all()
    return [{"slug": r.slug, "updated_at": r.updated_at} for r in rows]


@app.get("/genres")
def list_genres(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Genre.name, func.count(Anime.id))
        .join(Anime.genres).group_by(Genre.name).order_by(Genre.name)
    ).all()
    return [{"name": n, "count": c} for n, c in rows]


@app.get("/count")
def counts(db: Session = Depends(get_db)):
    """Total ringkas untuk sizing sitemap (anime, episode, movie)."""
    anime_n = db.scalar(select(func.count(Anime.id))) or 0
    ep_n = db.scalar(select(func.count(Episode.id)).where(Episode.number.is_not(None))) or 0
    movie_n = db.scalar(
        select(func.count(Anime.id)).where(func.lower(Anime.type) == "movie")) or 0
    return {"anime": anime_n, "episodes": ep_n, "movies": movie_n}


@app.get("/episodes")
def all_episodes(
    skip: int = 0,
    limit: int = Query(10000, le=50000),
    db: Session = Depends(get_db),
):
    """Semua episode (slug anime + nomor + created_at) untuk sitemap SEO.
    Hanya episode dengan nomor (URL /episode/{number} bisa diakses). Urutan
    stabil (anime_id, number) supaya paginasi konsisten antar-request."""
    rows = db.execute(text("""
        SELECT a.slug AS slug, e.number AS number, e.created_at AS created_at
        FROM episode e JOIN anime a ON a.id = e.anime_id
        WHERE e.number IS NOT NULL
        ORDER BY e.anime_id, e.number
        LIMIT :limit OFFSET :skip
    """), {"limit": limit, "skip": skip}).all()
    return [{"slug": r.slug, "number": r.number, "lastmod": r.created_at} for r in rows]


# ---------- Episode (link download, live-fetch) ----------
class DownloadGroup(BaseModel):
    resolution: Optional[str] = None
    size: Optional[str] = None
    hosts: list[dict] = []


class EpisodeReader(BaseModel):
    slug: str
    anime_slug: str
    number: str
    title: Optional[str] = None
    source_url: str
    stream_url: Optional[str] = None
    mirror_streams: list[dict] = []
    download_count: int
    downloads: list[DownloadGroup] = []
    prev_url: Optional[str] = None
    next_url: Optional[str] = None


# Cache halaman episode yang sudah diparse, {ep_url: (waktu, data)}. Cuma di
# memori (hilang saat restart) — biar reload tidak nembak Otakudesu berulang.
# Embed stream & link download jarang berubah, jadi TTL 1 jam aman dan
# mengurangi risiko IP server diblokir Otakudesu saat trafik tinggi.
_EPISODE_TTL = 3600         # detik
_EPISODE_CACHE_MAX = 5000   # entri; yang tertua dibuang supaya memori terbatas
_episode_cache: dict[str, tuple[float, dict]] = {}

# Hasil resolve `link.desustream.com/?id=...` -> link asli host. Pemetaannya
# tetap, jadi disimpan terpisah dan tidak ikut kedaluwarsa bersama episode.
_LINK_CACHE_MAX = 100_000
_link_cache: dict[str, str] = {}
_resolving: set[str] = set()
_resolve_lock = threading.Lock()
_resolve_pool = ThreadPoolExecutor(max_workers=10)


def _as_float(x: str) -> float | None:
    try:
        return float(x)
    except ValueError:
        return None


def _resolve_one(url: str) -> None:
    try:
        target = resolve_link(url)
        with _resolve_lock:
            _link_cache[url] = target
            if len(_link_cache) > _LINK_CACHE_MAX:
                _link_cache.pop(next(iter(_link_cache)))
    finally:
        with _resolve_lock:
            _resolving.discard(url)


def _resolve_in_background(downloads: list[dict]) -> None:
    """Resolve link download di thread terpisah, tidak ditunggu request.

    Resolve 1 link desustream bisa ±5 detik dan 1 episode punya ±15 link —
    kalau ditunggu, halaman episode baru tampil >10 detik (pengunjung kabur,
    Googlebot menganggap situs lambat). Selama belum selesai, link pembungkus
    tetap bisa diklik (desustream redirect 302 ke host yang sama).
    """
    urls = {h["url"] for g in downloads for h in g["hosts"] if h.get("url")}
    with _resolve_lock:
        todo = [u for u in urls if u not in _link_cache and u not in _resolving]
        _resolving.update(todo)
    for u in todo:
        _resolve_pool.submit(_resolve_one, u)


def _with_resolved(downloads: list[dict]) -> list[dict]:
    """Salinan `downloads` dengan link yang sudah diresolve diganti link asli."""
    return [
        {**g, "hosts": [{**h, "url": _link_cache.get(h.get("url"), h.get("url"))}
                        for h in g["hosts"]]}
        for g in downloads
    ]


def _episode_url(anime_slug: str, number: str, db: Session) -> str:
    """URL halaman episode di Otakudesu. Diambil dari DB (pola slug episode
    tiap judul berbeda & tak bisa disusun dari slug anime)."""
    ep = db.scalar(
        select(Episode).join(Anime, Episode.anime_id == Anime.id)
        .where(Anime.slug == anime_slug, Episode.number == _as_float(number))
    )
    if ep:
        return ep.url

    # Movie/one-shot: kalau anime hanya punya 1 episode, layani nomor apa pun
    # (mis. /episode/1) — datanya lama bisa punya number NULL.
    eps = db.scalars(
        select(Episode).join(Anime, Episode.anime_id == Anime.id)
        .where(Anime.slug == anime_slug)
    ).all()
    if len(eps) == 1:
        return eps[0].url

    raise HTTPException(404, "Episode tidak terdaftar di DB")


def _live_episode(ep_url: str, fresh: bool) -> dict:
    """Fetch + parse halaman episode (link download)."""
    hit = _episode_cache.get(ep_url)
    if hit and not fresh and (time.time() - hit[0]) < _EPISODE_TTL:
        data = hit[1]
    else:
        try:
            data = scrape_episode(ep_url)
        except HttpError as e:
            if e.status == 404:
                raise HTTPException(404, f"Episode tidak ada di Otakudesu: {ep_url}")
            raise HTTPException(502, f"Otakudesu balas HTTP {e.status}: {ep_url}")
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, f"Gagal ambil episode dari Otakudesu: {e}")
        # Mirror stream (±1 detik) ditunggu karena itu player-nya; link download
        # (lambat) diresolve di background — lihat _resolve_in_background.
        data["mirror_streams"] = resolve_mirror_streams(ep_url, data.get("mirrors", []))
        _episode_cache[ep_url] = (time.time(), data)
        if len(_episode_cache) > _EPISODE_CACHE_MAX:
            _episode_cache.pop(next(iter(_episode_cache)), None)
    _resolve_in_background(data["downloads"])
    return {**data, "downloads": _with_resolved(data["downloads"])}


@app.get("/anime/{anime_slug}/episode/{number}", response_model=EpisodeReader)
def read_episode(
    anime_slug: str,
    number: str,
    fresh: bool = Query(False, description="abaikan cache, fetch ulang"),
    db: Session = Depends(get_db),
):
    """Halaman episode — **live**: backend fetch halaman Otakudesu saat request
    masuk, ambil blok `.download` (link download per resolusi), lalu balikan.
    Tidak ada link yang disimpan di DB.

    Tiap host `url` jadi **link asli** (krakenfiles/pixeldrain/mega/dst) begitu
    pembungkus `link.desustream.com/?id=...` selesai diresolve di background.
    Request pertama bisa masih berisi pembungkus (tetap jalan: redirect 302);
    request berikutnya dapat link asli dari cache."""
    data = _live_episode(_episode_url(anime_slug, number, db), fresh)
    return {
        "slug": f"anime/{anime_slug}/episode/{number}",
        "anime_slug": anime_slug,
        "number": number,
        "title": data["title"],
        "source_url": data["source_url"],
        "stream_url": data["stream_url"],
        "mirror_streams": data["mirror_streams"],
        "download_count": data["download_count"],
        "downloads": data["downloads"],
        "prev_url": data["prev_url"],
        "next_url": data["next_url"],
    }


class IngestBody(BaseModel):
    url: str


@app.post("/ingest", status_code=202)
def ingest(body: IngestBody, background: BackgroundTasks):
    """Trigger scrape+simpan 1 URL anime (async, di background)."""
    background.add_task(ingest_url, body.url)
    return {"status": "queued", "url": body.url}
