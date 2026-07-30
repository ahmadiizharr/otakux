#!/usr/bin/env python3
"""
Otakudesu scraper (berbasis Scrapling).

- scrape_list(url)      -> daftar {title, slug, url, ...} dari halaman katalog
                           (mis. /ongoing-anime/, /complete-anime/, /anime-list/)
- scrape_detail(url)    -> dict lengkap 1 anime + daftar episode
- scrape_episode(url)   -> link download 1 episode (dikelompokkan per resolusi)

Semua fungsi mengembalikan data terstruktur (dict/list) siap dimasukkan ke DB.
"""
from __future__ import annotations
import base64
import http.cookiejar
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urljoin, urlparse
from scrapling.fetchers import Fetcher

BASE = "https://otakudesu.blog"

# Endpoint & action AJAX Otakudesu untuk meresolve mirror stream (data-content).
# Alur (dari JS halaman episode): POST action NONCE -> dapat nonce; lalu POST
# {id,i,q,nonce, action RESOLVE} -> {data:<base64 iframe>} -> ambil src.
# NB: action ter-obfuscate (md5) & bisa berubah sewaktu-waktu -> rapuh.
_AJAX_URL = f"{BASE}/wp-admin/admin-ajax.php"
_AJAX_NONCE_ACTION = "aa1208d27f29ca340c92c66d1926f13f"
_AJAX_RESOLVE_ACTION = "2a3505c93b0035d3f455df82bf976b84"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Cegah urllib mengikuti redirect supaya bisa baca header Location."""
    def redirect_request(self, *args):  # noqa: D401
        return None


_no_redirect_opener = urllib.request.build_opener(_NoRedirect)


def resolve_link(url: str, timeout: int = 15) -> str:
    """Ubah link redirect `link.desustream.com/?id=...` -> URL asli host.

    Situs Otakudesu membungkus tiap link download lewat `link.desustream.com`
    yang membalas **302** dengan header `Location` ke host asli (krakenfiles,
    pixeldrain, mega, dst). Fungsi ini GET tanpa mengikuti redirect lalu ambil
    `Location`. Kalau gagal/tanpa redirect, kembalikan URL semula (aman).
    """
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        r = _no_redirect_opener.open(req, timeout=timeout)
        return r.headers.get("Location") or url          # jarang: 200 langsung
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return e.headers.get("Location") or url
        return url
    except Exception:  # noqa: BLE001
        return url


def resolve_mirror_streams(episode_url: str, mirrors: list[dict],
                           timeout: int = 20, max_workers: int = 8) -> list[dict]:
    """Resolve tiap mirror (punya `data_content`) menjadi embed `stream_url`.

    Alur AJAX 2 langkah (lihat konstanta di atas): ambil nonce sekali, lalu
    POST {id,i,q,nonce} per mirror -> {data:<base64 iframe>} -> ambil `src`.
    Return [{quality, provider, stream_url}]; mirror yang gagal di-skip.
    """
    from concurrent.futures import ThreadPoolExecutor

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    hdr = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest",
           "Referer": episode_url, "Origin": BASE}

    def _post(data: dict) -> dict:
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(
            _AJAX_URL, data=body,
            headers={**hdr, "Content-Type":
                     "application/x-www-form-urlencoded; charset=UTF-8"})
        with opener.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    try:
        nonce = _post({"action": _AJAX_NONCE_ACTION}).get("data")
    except Exception:  # noqa: BLE001
        return []
    if not nonce:
        return []

    def _one(m: dict) -> dict | None:
        token = m.get("data_content")
        if not token:
            return None
        try:
            params = json.loads(base64.b64decode(token))
            res = _post({**params, "nonce": nonce,
                         "action": _AJAX_RESOLVE_ACTION})
            html = base64.b64decode(res["data"]).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            return None
        mm = re.search(r'src="([^"]+)"', html)
        if not mm:
            return None
        # Mega: pastikan bentuk /embed/ (bukan /file/) agar bisa di-embed.
        src = mm.group(1).replace("mega.nz/file/", "mega.nz/embed/")
        return {"quality": m.get("resolution"),
                "provider": m.get("name"), "stream_url": src}

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        out = list(ex.map(_one, mirrors))
    return [x for x in out if x]


class HttpError(RuntimeError):
    """Response non-200 dari Otakudesu; `status` dipakai API buat memetakan kode."""

    def __init__(self, status: int, url: str):
        super().__init__(f"HTTP {status} for {url}")
        self.status = status
        self.url = url


def _get(url: str):
    page = Fetcher.get(url, impersonate="chrome", timeout=40)
    if page.status != 200:
        raise HttpError(page.status, url)
    return page


def _first(node, sel):
    """css() -> first match atau None (Scrapling tak punya css_first)."""
    res = node.css(sel)
    return res[0] if res else None


def _slug_from_url(url: str) -> str:
    """URL anime -> slug.

    https://otakudesu.blog/anime/100-man-no-inochi-sub-indo/ -> 100-man-no-inochi-sub-indo
    """
    m = re.search(r"/anime/([^/]+)/?", url or "")
    return m.group(1) if m else (url or "").rstrip("/").split("/")[-1]


def _episode_number(text: str) -> float | None:
    """Ambil nomor episode dari judul/slug (mis. 'Episode 12 (End)' -> 12.0,
    'episode-7-5-sub-indo' -> 7.5). None kalau tak ketemu (batch/movie)."""
    if not text:
        return None
    m = re.search(r"[Ee]pisode[ \-]+(\d+(?:[.\-]\d+)?)", text)
    if not m:
        return None
    try:
        return float(m.group(1).replace("-", "."))
    except ValueError:
        return None


def scrape_list(url: str) -> list[dict]:
    """Ambil daftar anime dari halaman katalog Otakudesu.

    Kartu ada di `.venz ul li` (25/halaman). Mengembalikan data kartu:
    title, slug, url (halaman /anime/...), card_thumbnail, latest_episode.
    Ongoing/complete/homepage semuanya memakai markup yang sama.
    """
    page = _get(url)
    out = []
    for li in page.css(".venz ul li"):
        a = _first(li, ".thumb a") or _first(li, "a")
        href = a.attrib.get("href") if a else None
        full = urljoin(BASE, href) if href else None
        if not full or "/anime/" not in full:
            continue

        title_el = _first(li, ".jdlflm")
        title = title_el.get_all_text(strip=True) if title_el else None

        img = _first(li, "img")
        thumb = None
        if img:
            thumb = img.attrib.get("src") or img.attrib.get("data-src")

        ep_el = _first(li, ".epz")
        latest_episode = ep_el.get_all_text(strip=True) if ep_el else None

        out.append({
            "title": title,
            "slug": _slug_from_url(full),
            "url": full,
            "card_thumbnail": thumb,
            "latest_episode": latest_episode,
        })
    return out


def scrape_anime_list(url: str | None = None) -> list[dict]:
    """Ambil SELURUH katalog anime dari indeks A–Z `/anime-list/`.

    Tiap entri = `<a class="hodebgst">` berisi judul + href ke `/anime/{slug}/`.
    Satu halaman memuat semua judul (~1800+), jadi jauh lebih cepat daripada
    menyusuri ongoing/complete yang dipaginasi. Halaman ini TIDAK punya
    thumbnail/episode — thumbnail diisi via AniList (lihat anilist.py), detail
    lain via enrich_details.py. Return list {title, slug, url}.
    """
    if url is None:
        url = f"{BASE}/anime-list/"
    page = _get(url)
    out, seen = [], set()
    for a in page.css("a.hodebgst"):
        href = a.attrib.get("href")
        full = urljoin(BASE, href) if href else None
        if not full or "/anime/" not in full or full in seen:
            continue
        seen.add(full)
        out.append({
            "title": a.get_all_text(strip=True),
            "slug": _slug_from_url(full),
            "url": full,
        })
    return out


def _info_map(page) -> dict[str, str]:
    """Ubah blok `.infozingle p` (tiap <p> = '<b>Label</b>: value') jadi dict."""
    info = {}
    for p in page.css(".infozingle p"):
        b = _first(p, "b")
        if not b:
            continue
        full = p.get_all_text(strip=True)
        key = b.get_all_text(strip=True).rstrip(":").strip()
        # Nilai = teks setelah ':' pertama (label & nilai dipisah ':' oleh situs).
        val = full.split(":", 1)[1].strip() if ":" in full else ""
        info[key] = val
    return info


def _score(raw: str | None) -> float | None:
    if not raw:
        return None
    m = re.search(r"[\d.]+", raw)
    try:
        return float(m.group(0)) if m else None
    except ValueError:
        return None


def scrape_detail(url: str) -> dict:
    """Ambil semua field detail 1 anime + daftar episode."""
    page = _get(url)
    info = _info_map(page)

    # Genre = kumpulan <a> di dalam <p> berlabel "Genre".
    genres = []
    for p in page.css(".infozingle p"):
        b = _first(p, "b")
        if b and b.get_all_text(strip=True).rstrip(":").lower() == "genre":
            genres = [a.get_all_text(strip=True) for a in p.css("a")]
            break

    syn_el = _first(page, ".sinopc")
    synopsis = syn_el.get_all_text(strip=True) if syn_el else None

    img = _first(page, ".fotoanime img")
    thumbnail = img.attrib.get("src") if img else None

    # Episode: kumpulkan semua <li> di blok .episodelist yang menunjuk ke
    # /episode/ (lewati Batch di /batch/ dan link "download lengkap"). Dedup url.
    episodes = []
    seen: set[str] = set()
    for li in page.css(".episodelist ul li"):
        a = _first(li, "a")
        if not a:
            continue
        href = urljoin(BASE, a.attrib.get("href", ""))
        if "/episode/" not in href or href in seen:
            continue
        seen.add(href)
        name = a.get_all_text(strip=True)
        date_el = _first(li, ".zeebr")
        episodes.append({
            "name": name,
            "url": href,
            "number": _episode_number(name) or _episode_number(href),
            "released_at": date_el.get_all_text(strip=True) if date_el else None,
        })

    # Movie/one-shot: satu entri tanpa nomor "Episode N" -> anggap episode 1
    # supaya bisa diakses lewat /anime/{slug}/episode/1.
    if len(episodes) == 1 and episodes[0]["number"] is None:
        episodes[0]["number"] = 1.0

    title = info.get("Judul") or ""
    return {
        "slug": _slug_from_url(url),
        "title": title.strip(),
        "title_japanese": info.get("Japanese"),
        "type": info.get("Tipe"),
        "status": info.get("Status"),
        "score": _score(info.get("Skor")),
        "producers": info.get("Produser"),
        "studio": info.get("Studio"),
        "total_episode": info.get("Total Episode"),
        "duration": info.get("Durasi"),
        "release_date": info.get("Tanggal Rilis"),
        "genres": genres,
        "synopsis": synopsis,
        "thumbnail": thumbnail,
        "source_url": url,
        "episodes": episodes,
    }


def scrape_episode(url: str) -> dict:
    """Scrape halaman 1 episode: ambil link download per resolusi.

    Blok `.download ul li` = satu resolusi. Tiap li: <strong> resolusi,
    beberapa <a> (host mirror), <i> ukuran file. Mengembalikan daftar
    {resolution, size, hosts:[{name,url}]}.
    """
    page = _get(url)

    downloads = []
    for li in page.css(".download ul li"):
        res_el = _first(li, "strong")
        size_el = _first(li, "i")
        hosts = []
        for a in li.css("a"):
            href = a.attrib.get("href")
            if not href:
                continue
            hosts.append({
                "name": a.get_all_text(strip=True),
                "url": href,
            })
        if not hosts:
            continue
        downloads.append({
            "resolution": res_el.get_all_text(strip=True) if res_el else None,
            "size": size_el.get_all_text(strip=True) if size_el else None,
            "hosts": hosts,
        })

    # Fallback layout MOVIE/BD: sebagian halaman memakai blok `.yondarkness`
    # (bukan `ul li`). Judul memuat "[<resolusi>][<ukuran>]" lalu link host di
    # `.yondarkness-item a` (href asli link.desustream, data-wpel-link=external).
    if not downloads:
        titles = page.css(".download .yondarkness-title")
        items = page.css(".download .yondarkness-item")
        for t, it in zip(titles, items):
            bracket = re.findall(r"\[([^\]]+)\]", t.get_all_text(strip=True))
            hosts = [{"name": a.get_all_text(strip=True), "url": a.attrib.get("href")}
                     for a in it.css("a") if a.attrib.get("href")]
            if hosts:
                downloads.append({
                    "resolution": bracket[0] if len(bracket) >= 1 else None,
                    "size": bracket[1] if len(bracket) >= 2 else None,
                    "hosts": hosts,
                })

    # Streaming: iframe embed default sudah server-rendered di #pembed (tanpa
    # AJAX) — langsung dipasang di <iframe>. Ini mirror `data-default="true"`.
    iframe = _first(page, "#pembed iframe") or \
        _first(page, ".responsive-embed-stream iframe")
    stream_url = iframe.attrib.get("src") if iframe else None

    # Daftar mirror alternatif (butuh AJAX admin-ajax untuk resolve tiap embed;
    # di sini token `data_content` + meta saja, TIDAK diresolve).
    mirrors = []
    for ul_sel, res in ((".mirrorstream .m360p", "360p"),
                        (".mirrorstream .m480p", "480p"),
                        (".mirrorstream .m720p", "720p")):
        for a in page.css(ul_sel + " a"):
            mirrors.append({
                "name": a.get_all_text(strip=True),
                "resolution": res,
                "data_content": a.attrib.get("data-content"),
                "default": a.attrib.get("data-default") == "true",
            })

    h1 = _first(page, "h1.posttl") or _first(page, "h1")
    # Navigasi prev/next di .flir (teks "Previous Eps."/"Next Eps.").
    prev_url = next_url = None
    for a in page.css(".flir a"):
        label = a.get_all_text(strip=True).lower()
        href = urljoin(BASE, a.attrib.get("href", ""))
        if "previous" in label:
            prev_url = href
        elif "next" in label:
            next_url = href

    return {
        "title": h1.get_all_text(strip=True) if h1 else None,
        "source_url": url,
        "stream_url": stream_url,
        "mirrors": mirrors,
        "download_count": len(downloads),
        "downloads": downloads,
        "prev_url": prev_url,
        "next_url": next_url,
    }


if __name__ == "__main__":
    import sys, io, json
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    target = sys.argv[1] if len(sys.argv) > 1 else \
        "https://otakudesu.blog/anime/100-man-no-inochi-sub-indo/"
    if "/episode/" in target:
        data = scrape_episode(target)
    elif "/anime/" in target:
        data = scrape_detail(target)
    else:
        data = scrape_list(target)
    print(json.dumps(data, ensure_ascii=False, indent=2))
