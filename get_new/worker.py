#!/usr/bin/env python3
"""
Worker pengecek update chapter terbaru dari Komiku.

Cara kerja:
  1. Ambil daftar "update terbaru" dari htmx endpoint yang mengisi
     <div class="daftar"> di https://komiku.org/pustaka/ , yaitu:
         https://api.komiku.org/manga/          (halaman 1)
         https://api.komiku.org/manga/page/N/   (halaman N)
     Daftar ini diurutkan dari yang PALING BARU di-update.
  2. Tiap kartu (.bge) berisi link manga (.bgei a[href]) dan blok .new1
     "Terbaru:" yang menunjuk chapter paling akhir.
  3. Cek ke database (komiku_api/komiku.db):
       - kalau manga sudah ada TAPI chapter terbaru belum tercatat
         -> ada chapter baru: scrape halaman detail lalu upsert (chapter
            baru otomatis ditambahkan, idempoten by url).
       - kalau manga belum ada sama sekali -> ingest detail penuh (baru).
  4. Karena daftar terurut terbaru-dulu, kalau satu halaman penuh sudah
     tidak ada perubahan -> berhenti (early stop), kecuali --no-early-stop.

Mode jalan:
  python worker.py --once            # sekali jalan (instan) lalu keluar
  python worker.py                   # loop tiap 30 menit (default)
  python worker.py --interval 900    # loop tiap 15 menit
  python worker.py --pages 5         # cek maksimal 5 halaman tiap siklus
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

# --- Pakai ulang modul dari komiku_api (scraper + ingest + models DB) -------
ROOT = Path(__file__).resolve().parent.parent
KOMIKU_DIR = ROOT / "komiku_api"
sys.path.insert(0, str(KOMIKU_DIR))

import db  # noqa: E402
from sqlalchemy import create_engine, func, select  # noqa: E402

# Arahkan engine ke DB absolut komiku_api/komiku.db supaya tidak bergantung
# pada current working directory saat worker dijalankan. sessionmaker
# db.SessionLocal di-rebind (objeknya sama yang dipakai ingest.py), jadi
# upsert lewat ingest ikut memakai DB yang benar.
DB_PATH = KOMIKU_DIR / "komiku.db"
db.engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}", future=True)
db.SessionLocal.configure(bind=db.engine)

from db import SessionLocal, Manga, Chapter, init_db  # noqa: E402
from scraper import BASE, _first, _slug_from_url, _parse_chapter_url  # noqa: E402
from scrapling.fetchers import Fetcher  # noqa: E402
from ingest import ingest_url  # noqa: E402

API_BASE = "https://api.komiku.org/manga"


def _log(msg: str) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _clean(txt: str | None) -> str:
    """Rapikan teks label kartu jadi satu baris (buang newline berlebih)."""
    return " ".join((txt or "").split())


def _chapter_num(url: str) -> float | None:
    """Ambil nomor chapter dari URL chapter (mis. ...-chapter-870/ -> 870.0)."""
    _, num = _parse_chapter_url(url)
    if num is None:
        return None
    try:
        return float(num)
    except ValueError:
        return None


def _fetch_cards(page_num: int):
    """Ambil kartu .bge dari endpoint update terbaru (htmx .daftar)."""
    url = f"{API_BASE}/" if page_num <= 1 else f"{API_BASE}/page/{page_num}/"
    page = Fetcher.get(
        url, impersonate="chrome", timeout=30,
        headers={"Referer": f"{BASE}/"},
    )
    if page.status != 200:
        raise RuntimeError(f"HTTP {page.status} untuk {url}")
    return page.css(".bge")


def _parse_card(card) -> dict | None:
    """Kartu .bge -> {slug, manga_url, latest_url, latest_text}.

    latest = blok .new1 terakhir ("Terbaru:") -> chapter paling akhir.
    """
    a = _first(card, ".bgei a") or _first(card, ".kan a")
    if not a:
        return None
    manga_url = urljoin(BASE, a.attrib.get("href", ""))
    slug = _slug_from_url(manga_url)

    latest_url = latest_text = None
    for n in card.css(".new1"):          # urutan: "Awal:", lalu "Terbaru:"
        la = _first(n, "a")
        if not la:
            continue
        latest_url = urljoin(BASE, la.attrib.get("href", ""))
        latest_text = la.get_all_text(strip=True)
    if not manga_url or not latest_url:
        return None
    return {
        "slug": slug,
        "manga_url": manga_url,
        "latest_url": latest_url,
        "latest_text": latest_text,
    }


def _check_card(card_data: dict) -> str:
    """Bandingkan chapter terbaru vs DB, upsert bila perlu.

    Return salah satu: 'new_manga', 'updated', 'unchanged', 'error'.
    """
    slug = card_data["slug"]
    latest_url = card_data["latest_url"]
    latest_num = _chapter_num(latest_url)

    with SessionLocal() as s:
        m = s.scalar(select(Manga).where(Manga.slug == slug))
        manga_id = m.id if m else None
        cnt_before = 0
        db_max = None
        latest_known = False
        if manga_id is not None:
            cnt_before = s.query(Chapter).filter(
                Chapter.manga_id == manga_id).count()
            db_max = s.scalar(
                select(func.max(Chapter.number)).where(
                    Chapter.manga_id == manga_id))
            latest_known = s.scalar(
                select(Chapter.id).where(
                    Chapter.manga_id == manga_id,
                    Chapter.url == latest_url,
                )
            ) is not None

    # Manga sudah ada dan sudah up-to-date -> tidak perlu scrape.
    #   * by nomor : nomor chapter terbaru <= nomor tertinggi di DB
    #   * fallback : kalau nomor tak terparse, cek URL chapter persis
    if manga_id is not None:
        if latest_num is not None and db_max is not None and latest_num <= db_max:
            return "unchanged"
        if latest_num is None and latest_known:
            return "unchanged"

    # Butuh scrape detail (manga baru, atau ada indikasi chapter baru).
    try:
        ingest_url(card_data["manga_url"])
        with SessionLocal() as s:
            m2 = s.scalar(select(Manga).where(Manga.slug == slug))
            cnt_after = s.query(Chapter).filter(
                Chapter.manga_id == m2.id).count()
    except Exception as e:  # noqa: BLE001
        _log(f"  ! ERROR ingest {slug}: {e}")
        return "error"

    if manga_id is None:
        _log(f"  + MANGA BARU {slug} ({cnt_after} chapter) [{_clean(card_data['latest_text'])}]")
        return "new_manga"

    added = cnt_after - cnt_before
    if added <= 0:
        # Kartu list mengiklankan chapter yang halaman detailnya belum live.
        # DB tidak berubah -> perlakukan sebagai unchanged (jangan reset streak).
        _log(f"  ~ {slug}: {_clean(card_data['latest_text'])} belum live di "
             f"halaman detail (DB max {db_max}) -> 0 chapter baru")
        return "unchanged"

    _log(f"  * UPDATE {slug}: +{added} chapter (total {cnt_after}) "
         f"-> {_clean(card_data['latest_text'])}")
    return "updated"


def run_once(max_pages: int, delay: float, stop_after: int) -> dict:
    """Satu siklus pengecekan.

    Menyusuri daftar terbaru halaman demi halaman (1, 2, 3, ...). Berhenti
    setelah menemukan `stop_after` kartu BERUNTUN yang chapternya sudah ada
    semua di DB (default 30). Counter direset tiap ketemu perubahan, jadi
    kalau di page dalam masih ada update, worker lanjut lebih dalam.
    `max_pages` cuma batas pengaman. stop_after<=0 -> cek sampai max_pages.
    """
    stats = {"new_manga": 0, "updated": 0, "unchanged": 0, "error": 0, "cards": 0}
    streak = 0          # kartu 'unchanged' beruntun
    stopped = False
    for page_num in range(1, max_pages + 1):
        try:
            cards = _fetch_cards(page_num)
        except Exception as e:  # noqa: BLE001
            _log(f"halaman {page_num}: ERROR fetch {e}")
            break
        if not cards:
            _log(f"halaman {page_num}: 0 kartu -> selesai")
            break

        page_changes = 0
        for card in cards:
            data = _parse_card(card)
            if not data:
                continue
            stats["cards"] += 1
            result = _check_card(data)
            stats[result] += 1
            if result in ("new_manga", "updated"):
                page_changes += 1
                streak = 0                      # ada perubahan -> reset streak
            elif result == "unchanged":
                streak += 1
                if stop_after > 0 and streak >= stop_after:
                    stopped = True
                    break
            # 'error' -> tidak dihitung ke streak (biar aman, tetap lanjut)

        _log(f"halaman {page_num}: {len(cards)} kartu, {page_changes} perubahan "
             f"(streak sama={streak})")

        if stopped:
            _log(f"{stop_after} kartu beruntun sudah ada di DB -> stop")
            break
        time.sleep(delay)

    _log(f"Ringkasan: baru={stats['new_manga']} update={stats['updated']} "
         f"tetap={stats['unchanged']} error={stats['error']} "
         f"(dicek {stats['cards']} kartu)")
    return stats


def main() -> None:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    ap = argparse.ArgumentParser(description="Cek chapter terbaru Komiku -> DB")
    ap.add_argument("--once", action="store_true",
                    help="jalan sekali (instan) lalu keluar")
    ap.add_argument("--interval", type=int, default=1800,
                    help="jeda antar siklus dalam detik (default 1800 = 30 menit)")
    ap.add_argument("--stop-after", type=int, default=30,
                    help="berhenti setelah N kartu beruntun sudah ada di DB "
                         "(default 30). 0 = cek sampai batas --max-pages")
    ap.add_argument("--max-pages", type=int, default=100,
                    help="batas pengaman jumlah halaman per siklus (default 100)")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="jeda antar halaman (detik)")
    args = ap.parse_args()

    init_db()  # pastikan tabel ada

    if args.once:
        run_once(args.max_pages, args.delay, args.stop_after)
        return

    _log(f"Worker mulai. Cek tiap {args.interval}s "
         f"(stop setelah {args.stop_after} kartu sama beruntun, "
         f"maks {args.max_pages} halaman). Ctrl+C untuk berhenti.")
    while True:
        try:
            run_once(args.max_pages, args.delay, args.stop_after)
        except KeyboardInterrupt:
            _log("Dihentikan oleh user.")
            break
        except Exception as e:  # noqa: BLE001
            _log(f"Siklus ERROR: {e}")
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            _log("Dihentikan oleh user.")
            break


if __name__ == "__main__":
    main()
