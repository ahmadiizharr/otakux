"""
Komiku FastAPI  —  konsep REST API di atas hasil scraping.

Jalankan:
    uvicorn main:app --reload
Docs interaktif:
    http://127.0.0.1:8000/docs
"""
from __future__ import annotations
import time
from typing import Optional
from urllib.parse import quote
from fastapi import (
    FastAPI, Depends, HTTPException, Query, BackgroundTasks, Request, Response,
)
from pydantic import BaseModel
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session

from db import SessionLocal, Manga, Genre, Chapter, init_db
from ingest import ingest_url
from scraper import (
    scrape_chapter, proxy_image as _proxy, fetch_image, is_komiku_image,
    HttpError, BASE,
)

app = FastAPI(title="Komiku API", version="0.1.0",
              description="REST API katalog manga hasil scraping Komiku.")


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
class ChapterOut(BaseModel):
    name: str
    number: Optional[float] = None
    url: str
    released_at: Optional[str] = None

    class Config:
        from_attributes = True


class MangaListItem(BaseModel):
    slug: str
    title: str
    type: Optional[str] = None
    status: Optional[str] = None
    thumbnail: Optional[str] = None
    total_views: int = 0

    class Config:
        from_attributes = True


class MangaDetail(BaseModel):
    slug: str
    title: str
    title_alt: Optional[str] = None
    type: Optional[str] = None
    theme: Optional[str] = None
    author: Optional[str] = None
    status: Optional[str] = None
    age_rating: Optional[str] = None
    reading_direction: Optional[str] = None
    total_views: int = 0
    synopsis: Optional[str] = None
    thumbnail: Optional[str] = None
    source_url: str
    genres: list[str] = []
    chapters: list[ChapterOut] = []

    class Config:
        from_attributes = True


def _detail(m: Manga) -> MangaDetail:
    return MangaDetail(
        slug=m.slug, title=m.title, title_alt=m.title_alt, type=m.type,
        theme=m.theme, author=m.author, status=m.status,
        age_rating=m.age_rating, reading_direction=m.reading_direction,
        total_views=m.total_views, synopsis=m.synopsis, thumbnail=m.thumbnail,
        source_url=m.source_url,
        genres=[g.name for g in m.genres],
        chapters=[ChapterOut.model_validate(c) for c in m.chapters],
    )


# ---------- Endpoints ----------
@app.get("/manga", response_model=list[MangaListItem])
def list_manga(
    q: Optional[str] = Query(None, description="cari di judul"),
    genre: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Manga)
    if q:
        stmt = stmt.where(Manga.title.ilike(f"%{q}%"))
    if status:
        stmt = stmt.where(Manga.status == status)
    if type:
        stmt = stmt.where(Manga.type == type)
    if genre:
        stmt = stmt.join(Manga.genres).where(Genre.name == genre)
    stmt = stmt.order_by(Manga.total_views.desc()).offset(skip).limit(limit)
    return db.scalars(stmt).unique().all()


@app.get("/manga/{slug}", response_model=MangaDetail)
def get_manga(slug: str, db: Session = Depends(get_db)):
    m = db.scalar(select(Manga).where(Manga.slug == slug))
    if not m:
        raise HTTPException(404, "Manga tidak ditemukan")
    return _detail(m)


@app.get("/manga/{slug}/chapters", response_model=list[ChapterOut])
def get_chapters(slug: str, db: Session = Depends(get_db)):
    m = db.scalar(select(Manga).where(Manga.slug == slug))
    if not m:
        raise HTTPException(404, "Manga tidak ditemukan")
    return sorted(m.chapters, key=lambda c: (c.number or 0))


@app.get("/updates")
def latest_updates(
    skip: int = 0,
    limit: int = Query(24, le=60),
    db: Session = Depends(get_db),
):
    """Manga yang paling baru update, diurutkan dari tanggal rilis chapter
    terakhir. `released_at` tersimpan sebagai 'dd/mm/yyyy'; diubah jadi
    'yyyymmdd' supaya bisa di-sort sebagai string."""
    key = "substr(released_at,7,4)||substr(released_at,4,2)||substr(released_at,1,2)"
    # Recency = kapan chapter masuk ke DB (created_at, di-set saat scrape),
    # bukan sekadar tanggal rilis — supaya update terbaru yang benar muncul
    # paling atas alih-alih judul populer lama.
    rows = db.execute(text(f"""
        WITH latest AS (
            SELECT manga_id,
                   MAX(created_at) AS mc,
                   MAX(CASE WHEN released_at IS NOT NULL AND length(released_at) = 10
                            THEN {key} END) AS d
            FROM chapter
            GROUP BY manga_id
        )
        SELECT m.id, m.slug, m.title, m.type, m.status, m.thumbnail,
               m.total_views, latest.mc AS mc
        FROM latest JOIN manga m ON m.id = latest.manga_id
        ORDER BY latest.mc DESC, latest.d DESC
        LIMIT :limit OFFSET :skip
    """), {"limit": limit, "skip": skip}).all()

    out = []
    for r in rows:
        chaps = db.execute(text("""
            SELECT name, number, released_at
            FROM chapter
            WHERE manga_id = :mid
            ORDER BY created_at DESC, number DESC
            LIMIT 3
        """), {"mid": r.id}).all()
        out.append({
            "slug": r.slug, "title": r.title, "type": r.type,
            "status": r.status, "thumbnail": r.thumbnail,
            "total_views": r.total_views or 0,
            "latest_chapters": [
                {"name": c.name, "number": c.number, "released_at": c.released_at}
                for c in chaps
            ],
        })
    return out


@app.get("/slugs")
def all_slugs(db: Session = Depends(get_db)):
    """Semua slug + updated_at (buat sitemap SEO). Satu query, ringan."""
    rows = db.execute(text(
        "SELECT slug, updated_at FROM manga ORDER BY total_views DESC"
    )).all()
    return [{"slug": r.slug, "updated_at": r.updated_at} for r in rows]


@app.get("/count")
def counts(db: Session = Depends(get_db)):
    """Jumlah total manga, chapter, dan genre (buat sitemap + stats)."""
    return {
        "manga": db.scalar(select(func.count()).select_from(Manga)),
        "chapters": db.scalar(select(func.count()).select_from(Chapter)),
        "genres": db.scalar(select(func.count()).select_from(Genre)),
    }


@app.get("/chapters")
def chapter_urls(
    skip: int = 0,
    limit: int = Query(5000, le=10000),
    db: Session = Depends(get_db),
):
    """Daftar (slug, number, lastmod) semua chapter — buat sitemap halaman baca.
    lastmod diambil dari released_at ('dd/mm/yyyy' → 'yyyy-mm-dd'), fallback ke
    created_at. Diurutkan by chapter.id supaya paging stabil."""
    rows = db.execute(text("""
        SELECT m.slug AS slug, c.number AS number,
               c.released_at AS released_at, c.created_at AS created_at
        FROM chapter c JOIN manga m ON m.id = c.manga_id
        WHERE c.number IS NOT NULL
        ORDER BY c.id
        LIMIT :limit OFFSET :skip
    """), {"limit": limit, "skip": skip}).all()
    out = []
    for r in rows:
        ra = r.released_at
        if ra and len(ra) == 10:
            lastmod = f"{ra[6:10]}-{ra[3:5]}-{ra[0:2]}"
        else:
            lastmod = (r.created_at or "")[:10] or None
        out.append({"slug": r.slug, "number": r.number, "lastmod": lastmod})
    return out


@app.get("/genres")
def list_genres(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Genre.name, func.count(Manga.id))
        .join(Manga.genres).group_by(Genre.name).order_by(Genre.name)
    ).all()
    return [{"name": n, "count": c} for n, c in rows]


class ChapterReader(BaseModel):
    slug: str
    manga_slug: str
    chapter: str
    title: Optional[str] = None
    source_url: str
    image_count: int
    images: list[str] = []


# Cache halaman chapter yang sudah diparse, {chap_url: (waktu, data)}.
# Cuma di memori (hilang saat restart) — bukan penyimpanan, sekadar biar
# reload halaman tidak nembak Komiku berulang-ulang dalam waktu dekat.
_CHAPTER_TTL = 300          # detik
_chapter_cache: dict[str, tuple[float, dict]] = {}


def _chapter_url(manga_slug: str, number: str, db: Session) -> str:
    """URL halaman baca di Komiku. Ambil dari DB kalau chapter-nya terdaftar
    (pola URL tiap judul bisa beda: -chapter-1-1 vs -c-25), selain itu disusun
    dari slug + nomor."""
    ch = db.scalar(
        select(Chapter).join(Manga, Chapter.manga_id == Manga.id)
        .where(Manga.slug == manga_slug, Chapter.number == _as_float(number))
    )
    if ch:
        return ch.url
    return f"{BASE}/{manga_slug}-chapter-{number.replace('.', '-')}/"


def _live_chapter(chap_url: str, fresh: bool) -> dict:
    """Fetch + parse halaman chapter (URL gambar ASLI, belum dibungkus)."""
    hit = _chapter_cache.get(chap_url)
    if hit and not fresh and (time.time() - hit[0]) < _CHAPTER_TTL:
        return hit[1]
    try:
        data = scrape_chapter(chap_url, proxy=None)
    except HttpError as e:
        if e.status == 404:
            raise HTTPException(404, f"Chapter tidak ada di Komiku: {chap_url}")
        raise HTTPException(502, f"Komiku balas HTTP {e.status}: {chap_url}")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Gagal ambil chapter dari Komiku: {e}")
    if data["image_count"] == 0:
        raise HTTPException(404, f"Tidak ada gambar untuk {chap_url}")
    _chapter_cache[chap_url] = (time.time(), data)
    return data


@app.get("/manga/{manga_slug}/chapter/{number}", response_model=ChapterReader)
def read_chapter(
    request: Request,
    manga_slug: str,
    number: str,
    raw: bool = Query(False, description="true = URL gambar asli di CDN Komiku"),
    proxy: Optional[str] = Query(None, description="bungkus lewat proxy eksternal"),
    fresh: bool = Query(False, description="abaikan cache, fetch ulang"),
    db: Session = Depends(get_db),
):
    """Halaman baca — **live**: backend fetch halaman Komiku saat request masuk,
    ambil `#Baca_Komik img.ww`, lalu balikan daftar gambar. Tidak ada URL gambar
    yang disimpan di DB.

    Default `images` menunjuk ke `/img?url=...` (proxy backend), supaya bisa
    langsung dipasang di `<img>` — URL asli CDN Komiku akan 403 kalau diakses
    dari domain lain karena hotlink protection.

    - `?raw=true`   → URL asli CDN (perlu header Referer sendiri)
    - `?proxy=https://worker.dev` → bungkus pakai proxy eksternal
    """
    data = _live_chapter(_chapter_url(manga_slug, number, db), fresh)
    originals = data["images_raw"]

    if raw:
        images = originals
    elif proxy:
        images = [_proxy(u, proxy) for u in originals]
    else:
        base = str(request.base_url).rstrip("/")
        images = [f"{base}/img?url={quote(u, safe='')}" for u in originals]

    return {
        "slug": f"manga/{manga_slug}/chapter/{number}",
        "manga_slug": manga_slug,
        "chapter": number,
        "title": data["title"],
        "source_url": data["source_url"],
        "image_count": len(images),
        "images": images,
    }


@app.get("/img")
def image_proxy(url: str = Query(..., description="URL gambar di CDN Komiku")):
    """Streaming gambar lewat backend, dengan header Referer yang dibutuhkan CDN.

    Dibatasi ke host CDN Komiku saja supaya endpoint ini tidak jadi open proxy.
    """
    if not is_komiku_image(url):
        raise HTTPException(400, "Host tidak diizinkan (hanya CDN gambar Komiku)")
    try:
        body, ctype = fetch_image(url)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Gagal ambil gambar: {e}")
    return Response(content=body, media_type=ctype,
                    headers={"Cache-Control": "public, max-age=86400"})


def _as_float(x: str) -> float | None:
    try:
        return float(x)
    except ValueError:
        return None


class IngestBody(BaseModel):
    url: str


@app.post("/ingest", status_code=202)
def ingest(body: IngestBody, background: BackgroundTasks):
    """Trigger scrape+simpan 1 URL manga (async, di background)."""
    background.add_task(ingest_url, body.url)
    return {"status": "queued", "url": body.url}
