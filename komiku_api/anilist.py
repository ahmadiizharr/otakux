#!/usr/bin/env python3
"""
Ambil cover image anime dari AniList GraphQL — dipakai sebagai sumber utama
`anime.thumbnail` (Otakudesu tidak diandalkan untuk thumbnail).

Kenapa tanpa auth: query publik (search Media) TIDAK butuh OAuth/Client-Secret.
Client ID/Secret hanya untuk aksi atas nama user (mutation) — tidak dipakai di
sini, jadi tidak ada kredensial yang disimpan.

Hanya pakai stdlib (urllib) supaya tak menambah dependency. Hormati rate limit
AniList (~90 req/menit; balas 429 + header Retry-After).

Docs: https://docs.anilist.co/
"""
from __future__ import annotations
import json
import time
import urllib.error
import urllib.request

API = "https://graphql.anilist.co"

# Cari 1 anime paling relevan by judul, ambil coverImage beberapa ukuran.
_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    title { romaji english native }
    coverImage { extraLarge large medium }
  }
}
"""


class RateLimited(RuntimeError):
    """AniList balas 429; `retry_after` detik yang disarankan."""

    def __init__(self, retry_after: int):
        super().__init__(f"AniList 429 (retry after {retry_after}s)")
        self.retry_after = retry_after


def _post(query: str, variables: dict, timeout: int) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        API, data=body,
        # UA browser wajib: AniList di balik Cloudflare menolak UA default
        # "Python-urllib" dengan Error 1010 (403).
        headers={"Content-Type": "application/json",
                 "Accept": "application/json",
                 "User-Agent": "Mozilla/5.0 (OtakudesuAPI thumbnail fetcher)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise RateLimited(int(e.headers.get("Retry-After", "60") or 60))
        raise


def fetch_cover(title: str, size: str = "extraLarge", timeout: int = 20,
                retries: int = 4) -> str | None:
    """Return URL cover AniList untuk `title`, atau None kalau tak ketemu.

    `size`: extraLarge | large | medium (fallback berjenjang). Otomatis retry
    saat kena 429 (menunggu Retry-After).
    """
    if not title:
        return None
    for _ in range(retries):
        try:
            res = _post(_QUERY, {"search": title}, timeout)
        except RateLimited as e:
            time.sleep(e.retry_after + 1)
            continue
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None
        media = (res.get("data") or {}).get("Media")
        if not media:
            return None
        cover = media.get("coverImage") or {}
        return cover.get(size) or cover.get("large") or cover.get("medium")
    return None


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    q = sys.argv[1] if len(sys.argv) > 1 else \
        "100-man no Inochi no Ue ni Ore wa Tatteiru"
    print(q, "->", fetch_cover(q))
