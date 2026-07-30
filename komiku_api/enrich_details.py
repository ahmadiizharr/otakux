#!/usr/bin/env python3
"""
TAHAP 2 (resumable): isi detail penuh untuk manga yang belum didetailkan.

"Belum didetailkan" = synopsis IS NULL (crawl_catalog hanya isi data kartu).
Aman di-stop/di-ulang kapan saja: yang sudah terisi dilewati.

Contoh:
    python enrich_details.py --limit 50          # proses 50 berikutnya
    python enrich_details.py                      # proses SEMUA sisanya
    python enrich_details.py --delay 1.0
"""
from __future__ import annotations
import sys, io, time, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from sqlalchemy import select, func
from db import SessionLocal, Manga, init_db
from ingest import ingest_url


def pending_count() -> int:
    with SessionLocal() as s:
        return s.scalar(select(func.count()).select_from(Manga)
                        .where(Manga.synopsis.is_(None)))


def run(limit: int | None, delay: float) -> None:
    init_db()
    with SessionLocal() as s:
        stmt = select(Manga.source_url, Manga.title).where(Manga.synopsis.is_(None))
        if limit:
            stmt = stmt.limit(limit)
        targets = s.execute(stmt).all()

    total = len(targets)
    print(f"Akan diproses: {total} manga (sisa keseluruhan: {pending_count()})\n")
    ok, failed = 0, []
    for i, (url, title) in enumerate(targets, 1):
        try:
            ingest_url(url)
            ok += 1
            if i % 10 == 0 or i == total:
                print(f"[{i}/{total}] ok={ok} fail={len(failed)}  (terakhir: {title[:40]})")
        except Exception as e:  # noqa: BLE001
            failed.append((title, url, str(e)[:80]))
            print(f"[{i}/{total}] FAIL {title[:40]} -> {str(e)[:80]}")
        time.sleep(delay)

    print(f"\nSelesai batch. ok={ok} fail={len(failed)}  sisa global={pending_count()}")
    for t, u, e in failed[:20]:
        print(f"  - {t[:40]}: {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--delay", type=float, default=0.6)
    args = ap.parse_args()
    run(args.limit, args.delay)
