#!/usr/bin/env python3
"""
Komiku scraper (berbasis Scrapling).

- scrape_list(tipe, page)  -> daftar {title, slug, url} dari halaman /daftar-komik
- scrape_detail(url)       -> dict lengkap 1 manga + list chapter

Semua fungsi mengembalikan data terstruktur (dict/list) siap dimasukkan ke DB.
"""
from __future__ import annotations
import re
from urllib.parse import urljoin, quote, urlparse
from scrapling.fetchers import Fetcher

BASE = "https://komiku.org"

# Proxy Worker untuk gambar (format: {base}/?url=<url-encoded>).
# Default MATI (None) -> kembalikan URL gambar asli. Proxy dipasang nanti oleh
# konsumen API (mis. lewat ?proxy=... di endpoint) kalau memang butuh.
# Contoh Worker: https://silent-disk-c067.ginaderoli.workers.dev
IMAGE_PROXY = None


def proxy_image(src: str, proxy: str | None = IMAGE_PROXY) -> str:
    """Bungkus URL gambar lewat proxy Worker: {proxy}/?url=<encoded>.
    proxy=None -> kembalikan URL asli tanpa dibungkus."""
    if not proxy:
        return src
    return f"{proxy.rstrip('/')}/?url={quote(src, safe='')}"


# CDN gambar Komiku. Dipakai sebagai allowlist endpoint /img supaya endpoint itu
# tidak jadi open proxy (bisa dipakai orang buat fetch URL sembarangan lewat server kita).
IMAGE_HOSTS = {"img.komiku.org", "thumbnail.komiku.org"}


class HttpError(RuntimeError):
    """Response non-200 dari Komiku; `status` dipakai API buat memetakan kode."""

    def __init__(self, status: int, url: str):
        super().__init__(f"HTTP {status} for {url}")
        self.status = status
        self.url = url


def _get(url: str):
    page = Fetcher.get(url, impersonate="chrome", timeout=30)
    if page.status != 200:
        raise HttpError(page.status, url)
    return page


def is_komiku_image(url: str) -> bool:
    """True kalau URL menunjuk ke CDN gambar Komiku (dan http/https)."""
    try:
        u = urlparse(url)
    except ValueError:
        return False
    return u.scheme in ("http", "https") and u.hostname in IMAGE_HOSTS


def fetch_image(url: str) -> tuple[bytes, str]:
    """Ambil byte gambar dari CDN Komiku -> (bytes, content_type).

    CDN-nya pakai hotlink protection: tanpa header Referer komiku.org dia balas
    403 + HTML, bukan gambar. Karena itu request ini WAJIB bawa Referer.
    """
    r = Fetcher.get(url, impersonate="chrome", timeout=30,
                    headers={"Referer": f"{BASE}/"})
    ctype = (r.headers.get("content-type") or "").split(";")[0].strip()
    if r.status != 200:
        raise HttpError(r.status, url)
    if not ctype.startswith("image/"):
        raise RuntimeError(f"bukan gambar (content-type={ctype!r}) untuk {url}")
    return r.body, ctype


def _first(node, sel):
    """css() -> first match atau None (Scrapling tak punya css_first)."""
    res = node.css(sel)
    return res[0] if res else None


def _slug_from_url(url: str) -> str:
    # https://komiku.org/manga/50kg-cinderella/ -> 50kg-cinderella
    m = re.search(r"/manga/([^/]+)/?", url)
    return m.group(1) if m else url.rstrip("/").split("/")[-1]


def scrape_list(tipe: str | None = None, page_num: int = 1,
                url: str | None = None) -> list[dict]:
    """Ambil daftar manga dari halaman katalog.

    - url  : override URL penuh (mis. "https://komiku.org/daftar-komik/")
    - tipe : filter ?tipe=manga/manhwa/manhua (opsional)
    Mengembalikan data kartu: title, slug, url (a href), card_thumbnail,
    card_type, card_genre, card_status (dari <p class=meta>).
    """
    if url is None:
        q = f"?tipe={tipe}&page={page_num}" if tipe else (
            "" if page_num == 1 else f"?page={page_num}")
        url = f"{BASE}/daftar-komik/{q}"
    page = _get(url)
    out = []
    for card in page.css(".manga-card"):
        h4 = _first(card, "h4")
        a = _first(card, "a")
        if not h4:
            continue
        href = a.attrib.get("href") if a else None
        full = urljoin(BASE, href) if href else None

        # thumbnail ada di data-src (lazy load)
        img = _first(card, "img")
        thumb = None
        if img:
            thumb = img.attrib.get("data-src") or img.attrib.get("src")

        # meta: "Manga • Drama\nStatus: Ongoing"
        meta = _first(card, ".meta")
        card_type = card_genre = card_status = None
        if meta:
            txt = meta.get_all_text(strip=False)
            first_line = txt.strip().split("\n")[0]
            if "•" in first_line:
                parts = [p.strip() for p in first_line.split("•", 1)]
                card_type = parts[0] or None
                card_genre = parts[1] if len(parts) > 1 else None
            m = re.search(r"Status:\s*([A-Za-z]+)", txt)
            card_status = m.group(1) if m else None

        out.append({
            "title": h4.get_all_text(strip=True),
            "slug": _slug_from_url(full) if full else None,
            "url": full,
            "card_thumbnail": thumb,
            "card_type": card_type,
            "card_genre": card_genre,
            "card_status": card_status,
        })
    return out


def _info_map(page) -> dict[str, str]:
    """Ubah tabel .inftable jadi dict {label: value}."""
    info = {}
    for tr in page.css(".inftable tr"):
        tds = tr.css("td")
        if len(tds) >= 2:
            key = tds[0].get_all_text(strip=True).rstrip(":").strip()
            val = tds[1].get_all_text(strip=True)
            info[key] = val
    return info


def scrape_detail(url: str) -> dict:
    """Ambil semua field detail 1 manga + daftar chapter."""
    page = _get(url)
    info = _info_map(page)

    # Genre = kumpulan <a> di baris Genre
    genres = []
    for tr in page.css(".inftable tr"):
        label = _first(tr, "td")
        if label and label.get_all_text(strip=True).rstrip(":").lower() == "genre":
            genres = [a.get_all_text(strip=True) for a in tr.css("a")]
            break

    # Sinopsis
    syn_el = _first(page, "#Sinopsis p") or _first(page, ".sinopsis p")
    sinopsis = syn_el.get_all_text(strip=True) if syn_el else None

    # Thumbnail
    img = _first(page, "[itemprop=image]") or _first(page, ".ims img")
    thumbnail = img.attrib.get("src") if img else None

    # Total views (dari "Total: 15575 views, ...")
    views = None
    if info.get("Pembaca"):
        m = re.search(r"Total:\s*([\d.]+)", info["Pembaca"])
        if m:
            views = int(m.group(1).replace(".", ""))

    # Chapters
    chapters = []
    for tr in page.css("#Daftar_Chapter tr"):
        a = _first(tr, "a")
        if not a:
            continue  # header row
        tds = tr.css("td")
        chapters.append({
            "name": a.get_all_text(strip=True),
            "url": urljoin(BASE, a.attrib.get("href", "")),
            "released_at": tds[-1].get_all_text(strip=True) if len(tds) > 1 else None,
        })

    title = info.get("Judul") or ""
    return {
        "slug": _slug_from_url(url),
        "title": title.lstrip("-").strip(),
        "title_alt": info.get("Judul Alternatif"),
        "type": info.get("Tipe"),
        "theme": info.get("Tema"),
        "genres": genres,
        "author": info.get("Author"),
        "status": info.get("Status"),
        "age_rating": info.get("Rating"),          # cth "15+"
        "reading_direction": info.get("Cara Baca"),
        "total_views": views,
        "synopsis": sinopsis,
        "thumbnail": thumbnail,
        "source_url": url,
        "chapters": chapters,
    }


def _parse_chapter_url(url: str) -> tuple[str, str | None]:
    """URL chapter -> (manga_slug, nomor_chapter).

    https://komiku.org/50kg-cinderella-chapter-1-1/  -> ('50kg-cinderella', '1.1')
    https://komiku.org/...-c-25/                      -> (manga_slug, '25')
    Nomor: tanda '-' setelah 'chapter'/'c' diubah jadi '.'  (1-1 -> 1.1)
    """
    path = url.rstrip("/").split("/")[-1]
    for sep in ("-chapter-", "-c-"):
        if sep in path:
            manga_slug, num = path.rsplit(sep, 1)
            return manga_slug, num.replace("-", ".")
    return path, None


def scrape_chapter(url: str, proxy: str | None = IMAGE_PROXY) -> dict:
    """Scrape halaman baca 1 chapter: ambil semua gambar dari #Baca_Komik.

    Mengembalikan slug rapi 'manga/<slug>/chapter/<nomor>' + daftar gambar
    yang sudah dibungkus proxy (dan versi mentahnya).
    """
    page = _get(url)
    manga_slug, number = _parse_chapter_url(url)

    # Gambar halaman selalu <img class="klazy ww"> di dalam #Baca_Komik.
    # Pakai .ww supaya banner/iklan di container yang sama tidak ikut terambil;
    # fallback ke semua img kalau suatu chapter tidak memakai class itu.
    imgs = page.css("#Baca_Komik img.ww") or page.css("#Baca_Komik img")
    raw = []
    for im in imgs:
        src = im.attrib.get("src") or im.attrib.get("data-src")
        if src:
            raw.append(src)

    h1 = _first(page, "h1")
    return {
        "slug": f"manga/{manga_slug}/chapter/{number}",
        "manga_slug": manga_slug,
        "chapter": number,
        "title": h1.get_all_text(strip=True) if h1 else None,
        "source_url": url,
        "image_count": len(raw),
        "images": [proxy_image(s, proxy) for s in raw],
        "images_raw": raw,
    }


if __name__ == "__main__":
    import sys, io, json
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    target = sys.argv[1] if len(sys.argv) > 1 else "https://komiku.org/manga/50kg-cinderella/"
    if "-chapter-" in target or "-c-" in target:
        data = scrape_chapter(target)
    else:
        data = scrape_detail(target)
    print(json.dumps(data, ensure_ascii=False, indent=2))
