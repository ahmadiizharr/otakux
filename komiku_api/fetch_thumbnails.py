#!/usr/bin/env python3
"""
Isi kolom `anime.thumbnail` dari AniList (match by judul). Resumable.

Default hanya memproses anime yang `thumbnail IS NULL` (aman diulang). Pakai
`--force` untuk menimpa semua (mis. mau refresh cover). AniList publik & tanpa
auth (lihat anilist.py); jaga `--delay` wajar agar tak kena rate limit.

Contoh:
    python fetch_thumbnails.py                 # semua yang belum ada thumbnail
    python fetch_thumbnails.py --limit 100     # 100 pertama
    python fetch_thumbnails.py --force         # timpa semua
    python fetch_thumbnails.py --delay 1.0
"""
from __future__ import annotations
import sys, time, argparse
# reconfigure (bukan bungkus TextIOWrapper baru) supaya stdout tetap
# line-buffered di terminal — progres tampil real-time, tidak "diam".
sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select, func, update
from db import SessionLocal, Anime, init_db
from anilist import fetch_cover


def pending_count(force: bool) -> int:
    with SessionLocal() as s:
        stmt = select(func.count()).select_from(Anime)
        if not force:
            stmt = stmt.where(Anime.thumbnail.is_(None))
        return s.scalar(stmt)


def run(limit: int | None, delay: float, force: bool) -> None:
    init_db()
    with SessionLocal() as s:
        stmt = select(Anime.id, Anime.title)
        if not force:
            stmt = stmt.where(Anime.thumbnail.is_(None))
        if limit:
            stmt = stmt.limit(limit)
        targets = s.execute(stmt).all()

    total = len(targets)
    print(f"Akan diproses: {total} anime (sisa keseluruhan: {pending_count(force)})\n",
          flush=True)
    ok = miss = fail = 0
    for i, (aid, title) in enumerate(targets, 1):
        try:
            cover = fetch_cover(title)
        except Exception as e:  # noqa: BLE001
            fail += 1
            print(f"[{i}/{total}] FAIL {(title or '')[:45]} -> {str(e)[:60]}")
            time.sleep(delay)
            continue

        if cover:
            with SessionLocal() as s:
                s.execute(update(Anime).where(Anime.id == aid)
                          .values(thumbnail=cover))
                s.commit()
            ok += 1
        else:
            miss += 1  # AniList tak punya match untuk judul ini

        if i % 10 == 0 or i == total:
            print(f"[{i}/{total}] ok={ok} miss={miss} fail={fail}  "
                  f"(terakhir: {(title or '')[:40]})", flush=True)
        time.sleep(delay)

    print(f"\nSelesai. ok={ok} miss={miss} fail={fail}  "
          f"sisa global={pending_count(force)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--delay", type=float, default=0.8,
                    help="jeda antar request AniList (detik); default 0.8")
    ap.add_argument("--force", action="store_true",
                    help="timpa thumbnail yang sudah ada")
    args = ap.parse_args()
    run(args.limit, args.delay, args.force)
