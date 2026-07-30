#!/usr/bin/env python3
"""
Scrape SEMUA gambar tiap chapter untuk 1 manga -> simpan ke tabel chapter_image.

URL chapter diambil dari DB (hasil scrape_detail). Gambar disimpan sebagai
URL ASLI (tanpa proxy). Resumable: chapter yang sudah punya gambar dilewati.

Contoh:
    python scrape_images.py 50kg-cinderella
    python scrape_images.py 50kg-cinderella --delay 1.0 --force
"""
from __future__ import annotations
import sys, time, argparse
sys.stdout.reconfigure(encoding="utf-8")   # aman dipanggil berkali-kali / saat di-import

from sqlalchemy import select
from db import SessionLocal, Manga, Chapter, ChapterImage, init_db
from scraper import scrape_chapter


def save_images(chapter_id: int, image_urls: list[str]) -> int:
    """Simpan/replace daftar gambar untuk 1 chapter. Return jumlah gambar."""
    with SessionLocal() as s:
        ch = s.get(Chapter, chapter_id)
        ch.images.clear()          # replace supaya idempoten
        s.flush()
        for i, url in enumerate(image_urls, 1):
            ch.images.append(ChapterImage(page=i, image_url=url))
        s.commit()
        return len(image_urls)


def run(manga_slug: str, delay: float, force: bool) -> None:
    init_db()
    with SessionLocal() as s:
        m = s.scalar(select(Manga).where(Manga.slug == manga_slug))
        if not m:
            print(f"Manga '{manga_slug}' tidak ada di DB.")
            return
        chapters = [(c.id, c.name, c.number, c.url, len(c.images)) for c in m.chapters]
        title = m.title

    print(f"Manga: {title}  ({len(chapters)} chapter)\n")
    ok = skipped = 0
    total_img = 0
    failed = []
    for cid, name, number, url, have in sorted(chapters, key=lambda x: (x[2] or 0)):
        if have and not force:
            skipped += 1
            print(f"  SKIP {name:<14} (sudah ada {have} gambar)")
            continue
        try:
            data = scrape_chapter(url, proxy=None)     # simpan URL asli
            n = save_images(cid, data["images"])
            ok += 1
            total_img += n
            print(f"  OK   {name:<14} {n:>3} gambar")
        except Exception as e:  # noqa: BLE001
            failed.append((name, url, str(e)[:80]))
            print(f"  FAIL {name:<14} -> {str(e)[:80]}")
        time.sleep(delay)

    print(f"\nSelesai. chapter ok={ok} skip={skipped} fail={len(failed)} "
          f"| total gambar tersimpan={total_img}")
    for n, u, e in failed:
        print(f"  - {n}: {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?", default="50kg-cinderella")
    ap.add_argument("--delay", type=float, default=0.8)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    run(args.slug, args.delay, args.force)
