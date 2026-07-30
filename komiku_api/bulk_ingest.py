#!/usr/bin/env python3
"""
Bulk ingest: ambil semua kartu di /daftar-komik/ (50 manga) lalu
scrape detail tiap manga dan simpan ke DB.

Pakai jeda antar-request (default 1.0 dtk) agar sopan ke server.

Jalankan:
    python bulk_ingest.py                     # halaman default (50 manga)
    python bulk_ingest.py --delay 1.5
    python bulk_ingest.py --url https://komiku.org/daftar-komik/?tipe=manga
"""
from __future__ import annotations
import sys, io, time, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from scraper import scrape_list, scrape_detail
from ingest import upsert_manga, is_detailed
from db import init_db


def run(list_url: str | None, delay: float, force: bool = False) -> None:
    init_db()
    cards = scrape_list(url=list_url)
    print(f"Ditemukan {len(cards)} kartu di daftar-komik\n")

    ok, skipped, failed = 0, 0, []
    seen: set[str] = set()          # dedup dalam 1 run (judul/url sama antar-halaman)
    for i, card in enumerate(cards, 1):
        url = card["url"]
        slug = card["slug"]
        title = card["title"]

        # 1) sudah diproses di run ini? (mis. muncul lagi di page berikutnya)
        key = slug or url
        if key in seen:
            skipped += 1
            print(f"[{i:>2}/{len(cards)}] SKIP (duplikat di run ini)  {title}")
            continue
        seen.add(key)

        # 2) sudah pernah di-scrape detail di run sebelumnya? (kecuali --force)
        if not force and is_detailed(slug=slug, url=url):
            skipped += 1
            print(f"[{i:>2}/{len(cards)}] SKIP (sudah ada di DB)     {title}")
            continue

        try:
            data = scrape_detail(url)
            mid = upsert_manga(data)
            ok += 1
            print(f"[{i:>2}/{len(cards)}] OK  id={mid:<3} "
                  f"{data['type'] or '?':<7} {len(data['chapters']):>3}ch  {title}")
        except Exception as e:  # noqa: BLE001
            failed.append((title, url, str(e)))
            print(f"[{i:>2}/{len(cards)}] FAIL {title}  -> {e}")
        time.sleep(delay)

    print(f"\nSelesai. Sukses={ok}  Dilewati={skipped}  Gagal={len(failed)}")
    for t, u, e in failed:
        print(f"  - {t} ({u}): {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://komiku.org/daftar-komik/",
                    help="URL halaman daftar")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="jeda antar-request (detik)")
    ap.add_argument("--force", action="store_true",
                    help="scrape ulang walau sudah ada di DB")
    args = ap.parse_args()
    run(args.url, args.delay, args.force)
