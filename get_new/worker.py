#!/usr/bin/env python3
"""
Worker pengecek update episode terbaru dari Otakudesu.

Cara kerja:
  1. Ambil daftar "ongoing" (terurut terbaru-di-atas) dari:
         https://otakudesu.blog/ongoing-anime/            (halaman 1)
         https://otakudesu.blog/ongoing-anime/page/N/      (halaman N)
     Tiap kartu (.venz ul li) berisi link anime (/anime/...) dan
     `.epz` = nomor episode terbaru ("Episode 6").
  2. Cek ke database (komiku_api/anime.db):
       - anime sudah ada TAPI nomor episode terbaru > nomor tertinggi di DB
         -> ada episode baru: scrape detail lalu upsert (idempoten by url).
       - anime belum ada sama sekali -> ingest detail penuh (baru).
  3. Karena daftar terurut terbaru-dulu, kalau banyak kartu beruntun sudah
     tidak berubah -> berhenti (early stop), kecuali --stop-after 0.

Mode jalan:
  python worker.py --once            # sekali jalan (instan) lalu keluar
  python worker.py                   # loop tiap 12 jam (default)
  python worker.py --interval 900    # loop tiap 15 menit
  python worker.py --max-pages 5     # cek maksimal 5 halaman tiap siklus
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
API_DIR = ROOT / "komiku_api"
sys.path.insert(0, str(API_DIR))

import db  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from db import SessionLocal, Anime, Episode, init_db  # noqa: E402
from scraper import BASE, scrape_list, _episode_number  # noqa: E402
from ingest import ingest_url  # noqa: E402

ONGOING_BASE = f"{BASE}/ongoing-anime"


def _log(msg: str) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _clean(txt: str | None) -> str:
    return " ".join((txt or "").split())


def _fetch_cards(page_num: int) -> list[dict]:
    """Ambil kartu anime dari halaman ongoing (via scrape_list)."""
    url = f"{ONGOING_BASE}/" if page_num <= 1 else f"{ONGOING_BASE}/page/{page_num}/"
    return scrape_list(url)


def _check_card(card: dict) -> str:
    """Bandingkan nomor episode terbaru vs DB, upsert bila perlu.

    Return salah satu: 'new_anime', 'updated', 'unchanged', 'error'.
    """
    slug = card["slug"]
    latest_num = _episode_number(card.get("latest_episode") or "")

    with SessionLocal() as s:
        m = s.scalar(select(Anime).where(Anime.slug == slug))
        anime_id = m.id if m else None
        cnt_before = 0
        db_max = None
        if anime_id is not None:
            cnt_before = s.query(Episode).filter(
                Episode.anime_id == anime_id).count()
            db_max = s.scalar(
                select(func.max(Episode.number)).where(
                    Episode.anime_id == anime_id))

    # Anime sudah ada & sudah up-to-date (nomor episode terbaru <= max DB).
    if anime_id is not None and latest_num is not None and db_max is not None \
            and latest_num <= db_max:
        return "unchanged"

    # Butuh scrape detail (anime baru, atau ada indikasi episode baru).
    try:
        ingest_url(card["url"])
        with SessionLocal() as s:
            m2 = s.scalar(select(Anime).where(Anime.slug == slug))
            cnt_after = s.query(Episode).filter(
                Episode.anime_id == m2.id).count()
    except Exception as e:  # noqa: BLE001
        _log(f"  ! ERROR ingest {slug}: {e}")
        return "error"

    if anime_id is None:
        _log(f"  + ANIME BARU {slug} ({cnt_after} episode) "
             f"[{_clean(card.get('latest_episode'))}]")
        return "new_anime"

    added = cnt_after - cnt_before
    if added <= 0:
        # Kartu list mengiklankan episode yang halaman detailnya belum live.
        _log(f"  ~ {slug}: {_clean(card.get('latest_episode'))} belum live di "
             f"halaman detail (DB max {db_max}) -> 0 episode baru")
        return "unchanged"

    _log(f"  * UPDATE {slug}: +{added} episode (total {cnt_after}) "
         f"-> {_clean(card.get('latest_episode'))}")
    return "updated"


def run_once(max_pages: int, delay: float, stop_after: int) -> dict:
    """Satu siklus pengecekan. Menyusuri halaman ongoing 1,2,3,... dan berhenti
    setelah `stop_after` kartu BERUNTUN yang sudah up-to-date (default 30).
    Counter direset tiap ketemu perubahan. stop_after<=0 -> sampai max_pages."""
    stats = {"new_anime": 0, "updated": 0, "unchanged": 0, "error": 0, "cards": 0}
    streak = 0
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
            if not card.get("slug"):
                continue
            stats["cards"] += 1
            result = _check_card(card)
            stats[result] += 1
            if result in ("new_anime", "updated"):
                page_changes += 1
                streak = 0
            elif result == "unchanged":
                streak += 1
                if stop_after > 0 and streak >= stop_after:
                    stopped = True
                    break

        _log(f"halaman {page_num}: {len(cards)} kartu, {page_changes} perubahan "
             f"(streak sama={streak})")

        if stopped:
            _log(f"{stop_after} kartu beruntun sudah ada di DB -> stop")
            break
        time.sleep(delay)

    _log(f"Ringkasan: baru={stats['new_anime']} update={stats['updated']} "
         f"tetap={stats['unchanged']} error={stats['error']} "
         f"(dicek {stats['cards']} kartu)")
    return stats


def main() -> None:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    ap = argparse.ArgumentParser(description="Cek episode terbaru Otakudesu -> DB")
    ap.add_argument("--once", action="store_true",
                    help="jalan sekali (instan) lalu keluar")
    ap.add_argument("--interval", type=int, default=43200,
                    help="jeda antar siklus dalam detik (default 43200 = 12 jam)")
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
