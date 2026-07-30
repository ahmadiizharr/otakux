#!/usr/bin/env python3
"""
Crawl SEMUA halaman katalog -> simpan data level-kartu untuk tiap manga.

Ini TAHAP 1 (cepat): hanya title/slug/href/thumbnail/tipe/status.
Detail penuh (author, sinopsis, genre, chapter) diisi oleh enrich_details.py.

Berhenti otomatis saat sebuah halaman mengembalikan 0 kartu.

Contoh:
    python crawl_catalog.py --tipe manga            # semua manga
    python crawl_catalog.py                          # semua tipe (/daftar-komik/)
    python crawl_catalog.py --tipe manga --max 82 --delay 0.5
"""
from __future__ import annotations
import sys, io, time, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from scraper import scrape_list, BASE
from ingest import upsert_card
from db import init_db


def build_url(tipe: str | None, halaman: int) -> str:
    parts = []
    if tipe:
        parts.append(f"tipe={tipe}")
    if halaman > 1:
        parts.append(f"halaman={halaman}")
    q = ("?" + "&".join(parts)) if parts else ""
    return f"{BASE}/daftar-komik/{q}"


def run(tipe: str | None, max_pages: int, delay: float) -> None:
    init_db()
    total_new = total_seen = 0
    seen_slugs: set[str] = set()

    for h in range(1, max_pages + 1):
        url = build_url(tipe, h)
        try:
            cards = scrape_list(url=url)
        except Exception as e:  # noqa: BLE001
            print(f"halaman {h}: ERROR {e} -> stop")
            break
        if not cards:
            print(f"halaman {h}: 0 kartu -> selesai")
            break

        new_here = 0
        for card in cards:
            if not card.get("slug"):
                continue
            if card["slug"] in seen_slugs:
                continue
            seen_slugs.add(card["slug"])
            _id, is_new = upsert_card(card)
            total_seen += 1
            if is_new:
                new_here += 1
                total_new += 1
        print(f"halaman {h:>3}: {len(cards):>2} kartu ({new_here} baru)  "
              f"| kumulatif unik={len(seen_slugs)}")
        time.sleep(delay)

    print(f"\nSelesai. Total manga unik={len(seen_slugs)}  "
          f"(baru dimasukkan={total_new})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tipe", default="manga", help="manga/manhwa/manhua; kosongkan utk semua")
    ap.add_argument("--max", type=int, default=200, help="batas halaman (safety)")
    ap.add_argument("--delay", type=float, default=0.5)
    args = ap.parse_args()
    run(args.tipe or None, args.max, args.delay)
