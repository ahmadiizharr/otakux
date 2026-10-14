# CLAUDE.md — panduan untuk AI agent

Dokumen ini dibaca AI agent (Claude Code dkk.) untuk memahami proyek ini
**sebelum** mengubah kode. Baca dulu, lalu kerjakan. Semua komentar & dokumen
di repo ini berbahasa Indonesia — ikuti gaya itu.

## Ringkasan proyek

Katalog **anime** hasil scraping **Otakudesu** (<https://otakudesu.blog>). Dua
service yang berbagi satu database SQLite:

```
                 scrape live (per request, link download episode)
        ┌──────────────────────────────────────────────┐
        │                                                ▼
  komiku_api/  ── baca/tulis ─►  komiku_api/anime.db   ◄── tulis ──  get_new/
  (FastAPI/uvicorn, REST API)      (SQLite, shared)         (worker loop)
```

> Catatan: dulu proyek ini scraping **manga (Komiku)**; sekarang sudah diganti
> ke **anime (Otakudesu)**. Nama direktori (`komiku_api`) sengaja dibiarkan
> untuk menghindari churn besar, tapi seluruh model/endpoint sudah anime.

- **`komiku_api/`** — REST API + scraper + model DB. Sumber kebenaran skema.
  DB ada di `komiku_api/anime.db`.
- **`get_new/`** — worker yang loop mengecek episode terbaru dan menulis ke DB
  yang **sama** (`komiku_api/anime.db`). Memakai ulang modul dari `komiku_api/`
  (via `sys.path`).
- **`backend/`** — eksperimen terpisah (Cloudflare D1/R2, notes).
  **Tidak berhubungan**; jangan dicampur.

## Menjalankan

Satu perintah (dari root repo) menyalakan API + worker:

```bash
python run.py          # atau: run.bat di Windows
```

- `run.py` = supervisor: spawn kedua service, prefix log `[api]`/`[worker]`,
  Ctrl+C mematikan semua. API mati = fatal; worker mati = di-restart otomatis.
- Interpreter: **Python 3.13** sistem (punya `scrapling`, `fastapi`, `uvicorn`,
  `SQLAlchemy`). `backend/.venv` TIDAK punya deps ini — jangan dipakai.

## Peta file (komiku_api/)

| File                 | Isi                                                            |
|----------------------|----------------------------------------------------------------|
| `db.py`              | Model SQLAlchemy 2.0 (`Anime`/`Genre`/`Episode`) + engine/session. `DATABASE_URL` absolut ke `anime.db`. |
| `scraper.py`         | Fetch+parse Otakudesu via Scrapling: `scrape_anime_list`, `scrape_list`, `scrape_detail`, `scrape_episode`, `HttpError`, `BASE`. |
| `ingest.py`          | `ingest_url(url)` → scrape 1 anime → upsert (idempoten by slug/url episode). Thumbnail TIDAK ditulis di sini (milik AniList). |
| `anilist.py`         | `fetch_cover(title)` → cover image dari AniList GraphQL (publik, tanpa auth). Sumber utama `anime.thumbnail`. |
| `main.py`            | FastAPI app. Endpoint di bawah.                                |
| `crawl_catalog.py`   | Tahap 1 (cepat, 1 request): seed SEMUA judul dari `/anime-list/` (`a.hodebgst`). |
| `fetch_thumbnails.py`| Tahap 2a: isi `anime.thumbnail` dari AniList (match by judul, resumable). |
| `enrich_details.py`  | Tahap 2b: isi detail anime yang `synopsis IS NULL` (resumable). |
| `bulk_ingest.py`     | 1 halaman katalog + langsung detail (sampel cepat).            |
| `schema.sql`         | Skema SQL murni (referensi; DB dibuat oleh `init_db()`).        |

Pipeline seeding: `crawl_catalog.py` → `fetch_thumbnails.py` → `enrich_details.py`.

## Skema data

```
anime ──< anime_genre >── genre     (m2m)
  └──< episode                        (1-m, unik by url)
```

**Link download episode TIDAK disimpan di DB.** Endpoint episode live-fetch ke
Otakudesu tiap request. Penanda "anime sudah didetailkan" = kolom `synopsis`
terisi.

**Thumbnail = AniList, bukan Otakudesu.** `anime.thumbnail` diisi oleh
`fetch_thumbnails.py` (AniList cover by judul). `ingest.upsert_*` sengaja TIDAK
menimpa thumbnail (thumbnail Otakudesu cuma cadangan bila AniList tak match).

## Endpoint utama (main.py)

`GET /anime` (filter+paging) · `GET /anime/{slug}` · `/anime/{slug}/episodes` ·
`GET /anime/{slug}/episode/{number}` (live scrape: `stream_url` embed default +
`mirror_streams` [{quality,provider,stream_url}] via AJAX + link download; host
`url` langsung link asli — `link.desustream` diresolve otomatis) · `/updates` ·
`/genres` · `/slugs` · `POST /ingest`.

## Konvensi & aturan tak-tertulis

- **Komentar berbahasa Indonesia**, ringkas, jelaskan *kenapa* bukan *apa*.
- **Idempoten**: semua upsert aman diulang (by `slug` untuk anime, by `url`
  untuk episode). Jangan bikin path yang menghasilkan duplikat.
- **Dedup**: `ingest.is_detailed()` menandai anime yang sudah punya synopsis;
  worker melewati anime yang nomor episode terbarunya sudah <= max di DB.
- **SQLite path absolut** (`db.py`): jangan balik ke path relatif — itu bikin
  API salah DB tergantung CWD.

## Jebakan Otakudesu (WAJIB tahu sebelum ubah scraper)

- **Katalog lengkap ada di `/anime-list/`** (indeks A–Z, `a.hodebgst`, ~1800+
  anime, 1 halaman) — dipakai `crawl_catalog.py`. `/ongoing-anime/` &
  `/complete-anime/` (`.venz ul li`) hanya subset, dipakai worker `get_new`.
- **AniList di balik Cloudflare**: WAJIB kirim header `User-Agent` browser;
  UA default `Python-urllib` ditolak Error 1010 (403). Lihat `anilist.py`.
- **Paginasi katalog pakai `/page/N/`** (mis. `/ongoing-anime/page/2/`).
  Halaman 1 tanpa `/page/1/`. 25 kartu/halaman (`.venz ul li`).
- **Akhir katalog ditandai jumlah kartu = 0.** Fetch pakai `impersonate="chrome"`
  (situs cek UA/TLS); tanpa itu bisa ditolak.
- **Blok `.episodelist` muncul >1 kali** di halaman detail (Batch, Episode List,
  download-lengkap). Ambil hanya `<a>` yang href-nya mengandung `/episode/`
  (lewati `/batch/`), lalu dedup by url.
- **Slug episode ≠ slug anime.** Slug anime `100-man-no-inochi-sub-indo`, slug
  episode `10man-episode-12-sub-indo`. URL episode TIDAK bisa disusun dari slug
  anime — ambil dari DB (kolom `episode.url`).
- **Link download di `.download ul li`**: `<strong>` resolusi, banyak `<a>` host
  mirror, `<i>` ukuran file. Di-scrape live, tidak disimpan.
- **Movie/BD sebagian pakai layout lain** di dalam `.download`: `.yondarkness-title`
  (judul + `[<resolusi>][<ukuran>]`) + `.yondarkness-item a` (href asli). Parser
  `scrape_episode` fallback ke sini kalau `.download ul li` kosong. Movie =
  1 episode tanpa nomor → di-set jadi **episode 1** (akses `/episode/1`; endpoint
  juga fallback ke satu-satunya episode).
- **Mirror stream via AJAX admin-ajax** (`scraper.resolve_mirror_streams`): decode
  `data-content` (`{id,i,q}`), POST 2 langkah (action `_AJAX_NONCE_ACTION` →
  nonce, lalu `_AJAX_RESOLVE_ACTION` → `{data:<base64 iframe>}` → ambil `src`).
  Mega dinormalkan ke `/embed/`. **Action ter-obfuscate (md5) & bisa berubah** —
  kalau `mirror_streams` tiba-tiba kosong, cek ulang action/nonce di JS halaman
  episode. `stream_url` default TIDAK butuh AJAX (dari `#pembed iframe`).
- **Host link dibungkus `link.desustream.com/?id=<base64>`** yang balas **302**
  ke host asli (krakenfiles/pixeldrain/mega/dst). `scraper.resolve_link()` ambil
  header `Location` (GET tanpa ikuti redirect). Resolve itu lambat (±5 dtk/link),
  jadi endpoint episode meresolve **di background** (`_resolve_in_background`,
  hasil di `_link_cache` tanpa TTL) dan tidak menunggunya: request pertama bisa
  masih berisi pembungkus (tetap jalan via 302), berikutnya link asli. Data
  episode (stream + mirror) di-cache 1 jam.

## Tugas umum → mulai dari mana

- Tambah/ubah field anime → `db.py` (model) + `scraper.scrape_detail` (parse) +
  `ingest.upsert_anime` (simpan) + schema respons di `main.py`.
- Tambah endpoint → `main.py` (pakai `Depends(get_db)` untuk session).
- Ubah logika "episode baru" → `get_new/worker.py` (`_check_card`).
- Ubah cara crawl massal → `crawl_catalog.py` / `enrich_details.py`.

## Uji cepat setelah perubahan

```bash
python run.py --api-only      # nyalakan API saja
curl "http://127.0.0.1:8081/anime?limit=1"
```

Worker bisa dites tanpa loop: `python get_new/worker.py --once --max-pages 1`.
