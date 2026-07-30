#!/usr/bin/env python3
"""
Bulk ingest: ambil semua kartu di 1 halaman katalog Otakudesu (25 anime)
lalu scrape detail tiap anime dan simpan ke DB. Sampel cepat.

Pakai jeda antar-request (default 1.0 dtk) agar sopan ke server.

Jalankan:
    python bulk_ingest.py                          # /ongoing-anime/ (halaman 1)
    python bulk_ingest.py --url https://otakudesu.blog/complete-anime/
    python bulk_ingest.py --delay 1.5 --force
"""
from __future__ import annotations
import sys, io, time, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from scraper import scrape_list, scrape_detail, BASE
from ingest import upsert_anime, is_detailed
from db import init_db


def run(list_url: str, delay: float, force: bool = False) -> None:
    init_db()
    cards = scrape_list(list_url)
    print(f"Ditemukan {len(cards)} kartu di {list_url}\n")

    ok, skipped, failed = 0, 0, []
    seen: set[str] = set()          # dedup dalam 1 run
    for i, card in enumerate(cards, 1):
        url = card["url"]
        slug = card["slug"]
        title = card["title"]

        key = slug or url
        if key in seen:
            skipped += 1
            print(f"[{i:>2}/{len(cards)}] SKIP (duplikat di run ini)  {title}")
            continue
        seen.add(key)

        # sudah pernah di-scrape detail di run sebelumnya? (kecuali --force)
        if not force and is_detailed(slug=slug, url=url):
            skipped += 1
            print(f"[{i:>2}/{len(cards)}] SKIP (sudah ada di DB)     {title}")
            continue

        try:
            data = scrape_detail(url)
            mid = upsert_anime(data)
            ok += 1
            print(f"[{i:>2}/{len(cards)}] OK  id={mid:<3} "
                  f"{data['type'] or '?':<4} {len(data['episodes']):>3}ep  {title}")
        except Exception as e:  # noqa: BLE001
            failed.append((title, url, str(e)))
            print(f"[{i:>2}/{len(cards)}] FAIL {title}  -> {e}")
        time.sleep(delay)

    print(f"\nSelesai. Sukses={ok}  Dilewati={skipped}  Gagal={len(failed)}")
    for t, u, e in failed:
        print(f"  - {t} ({u}): {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=f"{BASE}/ongoing-anime/",
                    help="URL halaman katalog (default /ongoing-anime/)")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="jeda antar-request (detik)")
    ap.add_argument("--force", action="store_true",
                    help="scrape ulang walau sudah ada di DB")
    args = ap.parse_args()
    run(args.url, args.delay, args.force)
