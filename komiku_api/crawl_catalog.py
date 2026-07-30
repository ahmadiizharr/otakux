#!/usr/bin/env python3
"""
Seed katalog dari indeks A–Z Otakudesu `/anime-list/` (SEMUA anime sekaligus).

Ini TAHAP 1 (cepat, 1 request): simpan title/slug/url tiap anime. Thumbnail
diisi via AniList (`fetch_thumbnails.py`), detail lain (sinopsis/genre/episode)
via `enrich_details.py`.

Urutan pipeline yang disarankan:
    python crawl_catalog.py        # seed semua judul dari /anime-list/
    python fetch_thumbnails.py     # isi thumbnail dari AniList
    python enrich_details.py       # isi sinopsis/genre/episode per anime

Contoh:
    python crawl_catalog.py
    python crawl_catalog.py --url https://otakudesu.blog/anime-list/
"""
from __future__ import annotations
import sys, argparse
sys.stdout.reconfigure(encoding="utf-8")   # line-buffered: progres real-time

from scraper import scrape_anime_list, BASE
from ingest import upsert_card
from db import init_db


def run(url: str) -> None:
    init_db()
    entries = scrape_anime_list(url)
    print(f"{len(entries)} anime di {url}\n")

    total_new = 0
    for i, e in enumerate(entries, 1):
        if not e.get("slug"):
            continue
        _id, is_new = upsert_card(e)   # {title, slug, url}; thumbnail via AniList
        if is_new:
            total_new += 1
        if i % 200 == 0 or i == len(entries):
            print(f"[{i}/{len(entries)}] disimpan  (baru={total_new})")

    print(f"\nSelesai. Total anime={len(entries)}  (baru dimasukkan={total_new})")
    print("Lanjut: python fetch_thumbnails.py  &&  python enrich_details.py")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=f"{BASE}/anime-list/",
                    help="URL indeks anime (default /anime-list/)")
    args = ap.parse_args()
    run(args.url)
