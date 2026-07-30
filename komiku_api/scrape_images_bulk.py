#!/usr/bin/env python3
"""
Scrape gambar chapter untuk BANYAK manga sekaligus (batch per N judul).

Sumber gambar: <img class="ww"> di dalam #Baca_Komik pada halaman baca
(lihat scraper.scrape_chapter). URL disimpan ASLI tanpa proxy ke chapter_image.

Resumable di dua level:
  - judul  : judul yang semua chapter-nya sudah punya gambar tidak dipilih lagi
  - chapter: chapter yang sudah punya gambar dilewati (kecuali --force)

Jadi aman di-stop kapan saja lalu dijalankan ulang untuk 10 judul berikutnya.

Contoh:
    python scrape_images_bulk.py                        # 10 judul berikutnya
    python scrape_images_bulk.py --titles 10 --delay 1.0
    python scrape_images_bulk.py --slug 50kg-cinderella --slug hack-g-u
    python scrape_images_bulk.py --titles 5 --max-chapters 3   # sampel cepat
    python scrape_images_bulk.py --titles 10 --dry-run         # lihat antrean saja
"""
from __future__ import annotations
import sys, time, argparse
sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select, func
from db import SessionLocal, Manga, Chapter, ChapterImage, init_db
from scraper import scrape_chapter
from scrape_images import save_images


def pick_titles(limit: int, slugs: list[str] | None, force: bool) -> list[tuple[str, str]]:
    """Pilih judul yang mau digarap -> [(slug, title)].

    Tanpa --slug: ambil manga yang punya chapter tapi masih ada chapter tanpa
    gambar, urut id (deterministik, jadi tiap run lanjut ke judul berikutnya).
    """
    with SessionLocal() as s:
        if slugs:
            rows = s.execute(
                select(Manga.slug, Manga.title).where(Manga.slug.in_(slugs))
            ).all()
            found = {r[0] for r in rows}
            for miss in [x for x in slugs if x not in found]:
                print(f"  ! slug '{miss}' tidak ada di DB, dilewati")
            return [(r[0], r[1]) for r in rows]

        has_chapter = select(Chapter.id).where(Chapter.manga_id == Manga.id)
        q = select(Manga.slug, Manga.title).where(has_chapter.exists())
        if not force:
            # sisakan hanya manga yang masih punya chapter tanpa gambar
            no_img = (
                select(Chapter.id)
                .where(
                    Chapter.manga_id == Manga.id,
                    ~select(ChapterImage.id)
                    .where(ChapterImage.chapter_id == Chapter.id)
                    .exists(),
                )
            )
            q = q.where(no_img.exists())
        return [(r[0], r[1]) for r in s.execute(q.order_by(Manga.id).limit(limit)).all()]


def chapters_of(slug: str) -> list[tuple[int, str, float | None, str, int]]:
    """-> [(chapter_id, name, number, url, jumlah_gambar_sekarang)] urut nomor."""
    with SessionLocal() as s:
        m = s.scalar(select(Manga).where(Manga.slug == slug))
        if not m:
            return []
        rows = [(c.id, c.name, c.number, c.url, len(c.images)) for c in m.chapters]
    return sorted(rows, key=lambda x: (x[2] or 0))


def scrape_one(slug: str, title: str, delay: float, force: bool,
               max_chapters: int | None) -> dict:
    """Garap 1 judul. Return statistik ringkas."""
    chapters = chapters_of(slug)
    if max_chapters:
        chapters = chapters[:max_chapters]

    stat = {"slug": slug, "title": title, "chapters": len(chapters),
            "ok": 0, "skip": 0, "fail": 0, "images": 0, "errors": []}

    print(f"\n=== {title}  ({slug})  {len(chapters)} chapter ===")
    for cid, name, _num, url, have in chapters:
        if have and not force:
            stat["skip"] += 1
            continue
        try:
            data = scrape_chapter(url, proxy=None)       # simpan URL asli
            n = save_images(cid, data["images"])
            stat["ok"] += 1
            stat["images"] += n
            flag = "" if n else "   <-- KOSONG, cek selector/halaman"
            print(f"  OK   {name:<16} {n:>3} gambar{flag}")
        except Exception as e:                            # noqa: BLE001
            stat["fail"] += 1
            stat["errors"].append((name, str(e)[:90]))
            print(f"  FAIL {name:<16} -> {str(e)[:90]}")
        time.sleep(delay)

    if stat["skip"]:
        print(f"  ({stat['skip']} chapter dilewati, sudah ada gambar)")
    print(f"  -> ok={stat['ok']} skip={stat['skip']} fail={stat['fail']} "
          f"gambar={stat['images']}")
    return stat


def run(titles: int, slugs: list[str] | None, delay: float, force: bool,
        max_chapters: int | None, dry_run: bool) -> None:
    init_db()
    targets = pick_titles(titles, slugs, force)
    if not targets:
        print("Tidak ada judul yang perlu digarap. "
              "Semua manga yang punya chapter sudah punya gambar.")
        return

    print(f"Antrean {len(targets)} judul:")
    for i, (slug, title) in enumerate(targets, 1):
        print(f"  {i:>2}. {title[:48]:<48} ({slug})")
    if dry_run:
        print("\n--dry-run: tidak ada yang di-scrape.")
        return

    stats = [scrape_one(slug, title, delay, force, max_chapters)
             for slug, title in targets]

    print("\n" + "=" * 72)
    print(f"{'JUDUL':<44} {'CH':>4} {'OK':>4} {'SKIP':>5} {'FAIL':>5} {'GAMBAR':>7}")
    print("-" * 72)
    for st in stats:
        print(f"{st['title'][:44]:<44} {st['chapters']:>4} {st['ok']:>4} "
              f"{st['skip']:>5} {st['fail']:>5} {st['images']:>7}")
    print("-" * 72)
    print(f"{'TOTAL':<44} {sum(s['chapters'] for s in stats):>4} "
          f"{sum(s['ok'] for s in stats):>4} {sum(s['skip'] for s in stats):>5} "
          f"{sum(s['fail'] for s in stats):>5} "
          f"{sum(s['images'] for s in stats):>7}")

    bad = [(s['title'], e) for s in stats for e in s['errors']]
    if bad:
        print(f"\n{len(bad)} chapter gagal:")
        for t, (name, err) in bad[:20]:
            print(f"  - {t[:30]} / {name}: {err}")

    with SessionLocal() as s:
        left = s.scalar(
            select(func.count(func.distinct(Manga.id)))
            .select_from(Manga).join(Chapter, Chapter.manga_id == Manga.id)
            .where(~select(ChapterImage.id)
                   .where(ChapterImage.chapter_id == Chapter.id).exists())
        )
    print(f"\nSisa judul yang belum lengkap gambarnya: {left}")
    print("Jalankan lagi perintah yang sama untuk 10 judul berikutnya.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Scrape gambar chapter untuk banyak manga (batch per N judul).")
    ap.add_argument("--titles", type=int, default=10,
                    help="jumlah judul per run (default 10)")
    ap.add_argument("--slug", action="append", dest="slugs",
                    help="target slug spesifik (boleh diulang); mengabaikan --titles")
    ap.add_argument("--delay", type=float, default=0.8,
                    help="jeda detik antar request chapter (default 0.8)")
    ap.add_argument("--max-chapters", type=int, default=None,
                    help="batasi N chapter pertama per judul (untuk sampel)")
    ap.add_argument("--force", action="store_true",
                    help="scrape ulang chapter yang sudah punya gambar")
    ap.add_argument("--dry-run", action="store_true",
                    help="tampilkan antrean judul lalu keluar")
    a = ap.parse_args()
    run(a.titles, a.slugs, a.delay, a.force, a.max_chapters, a.dry_run)
