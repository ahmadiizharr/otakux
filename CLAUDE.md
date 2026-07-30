# CLAUDE.md — panduan untuk AI agent

Dokumen ini dibaca AI agent (Claude Code dkk.) untuk memahami proyek ini
**sebelum** mengubah kode. Baca dulu, lalu kerjakan. Semua komentar & dokumen
di repo ini berbahasa Indonesia — ikuti gaya itu.

## Ringkasan proyek

Katalog manga hasil scraping **Komiku** (<https://komiku.org>). Dua service
yang berbagi satu database SQLite:

```
                 scrape live (per request, gambar)
        ┌──────────────────────────────────────────────┐
        │                                                ▼
  komiku_api/  ── baca/tulis ─►  komiku_api/komiku.db  ◄── tulis ──  get_new/
  (FastAPI/uvicorn, REST API)      (SQLite, shared)         (worker loop)
```

- **`komiku_api/`** — REST API + scraper + model DB. Sumber kebenaran skema.
- **`get_new/`** — worker yang loop mengecek chapter terbaru dan menulis ke DB
  yang **sama** (`komiku_api/komiku.db`). Memakai ulang modul `komiku_api/`.
- **`backend/`** — eksperimen terpisah (Cloudflare D1/R2, catatan/notes).
  **Tidak berhubungan** dengan komiku_api/get_new; jangan dicampur.
- **`temp/`** — scratch, boleh diabaikan.

## Menjalankan

Satu perintah menyalakan API + worker (lihat [README.md](README.md)):

```bash
python run.py          # atau: run.bat di Windows
```

- [run.py](run.py) = supervisor: spawn kedua service, prefix log
  `[api]`/`[worker]`, Ctrl+C mematikan semua. API mati = fatal; worker mati =
  di-restart otomatis.
- Interpreter: **Python 3.13** sistem (punya `scrapling`, `fastapi`, `uvicorn`,
  `SQLAlchemy`). `backend/.venv` TIDAK punya deps ini — jangan dipakai untuk
  komiku_api/get_new.

## Peta file (komiku_api/)

| File                 | Isi                                                            |
|----------------------|----------------------------------------------------------------|
| `db.py`              | Model SQLAlchemy 2.0 (`Manga`/`Genre`/`Chapter`) + engine/session. `DATABASE_URL` absolut ke `komiku_api/komiku.db`. |
| `scraper.py`         | Fetch+parse Komiku via Scrapling. `scrape_detail`, `scrape_chapter`, `fetch_image`, `IMAGE_HOSTS`, `HttpError`. Data terstruktur (dict/list). |
| `ingest.py`          | `ingest_url(url)` → scrape 1 manga → upsert (idempoten by slug/url chapter). |
| `main.py`            | FastAPI app. Endpoint di bawah.                                |
| `crawl_catalog.py`   | Tahap 1: crawl semua halaman katalog (level kartu).            |
| `enrich_details.py`  | Tahap 2: isi detail manga yang `synopsis IS NULL` (resumable). |
| `bulk_ingest.py`     | 1 halaman daftar + langsung detail (sampel cepat).             |
| `schema.sql`         | Skema SQL murni (referensi; DB dibuat oleh `init_db()`).        |

`get_new/worker.py` mengimpor `db`, `scraper`, `ingest` dari `komiku_api/`
(via `sys.path`) supaya logika scrape/upsert konsisten.

## Skema data

```
manga ──< manga_genre >── genre     (m2m)
  └──< chapter                        (1-m, unik by url)
```

**Gambar halaman TIDAK disimpan di DB.** Endpoint reader live-fetch ke Komiku
tiap request. Penanda "manga sudah didetailkan" = kolom `synopsis` terisi.

## Endpoint utama (main.py)

`GET /manga` (filter+paging) · `GET /manga/{slug}` · `/manga/{slug}/chapters` ·
`GET /manga/{slug}/chapter/{number}` (live scrape) · `GET /img?url=` (proxy
gambar) · `/updates` · `/genres` · `/slugs` · `POST /ingest`.

## Konvensi & aturan tak-tertulis

- **Komentar berbahasa Indonesia**, ringkas, jelaskan *kenapa* bukan *apa*.
- **Idempoten**: semua upsert aman diulang (by `slug` untuk manga, by `url`
  untuk chapter). Jangan bikin path yang menghasilkan duplikat.
- **Dedup**: scraper melewati manga yang `is_detailed()`; worker melewati
  chapter yang sudah tercatat.
- **SQLite path absolut** (`db.py`): jangan balik ke path relatif — itu bikin
  API salah DB tergantung CWD. Kalau butuh DB lain, ganti lewat env, bukan
  hardcode relatif.

## Jebakan Komiku (WAJIB tahu sebelum ubah scraper)

- **Paginasi pakai `?halaman=N`, bukan `?page=N`.** `page` diam-diam balik ke
  halaman 1. Halaman 1 tanpa parameter. 50 kartu/halaman.
- **Akhir katalog ditandai jumlah kartu = 0, BUKAN HTTP 404.** Halaman di luar
  batas tetap balas 200 dengan body normal tanpa `.manga-card`.
- **Hotlink protection gambar.** `img.komiku.org` balas 403 tanpa header
  `Referer: https://komiku.org/`. Karena itu ada `/img` (memasang Referer di
  server). `/img` dibatasi ke `scraper.IMAGE_HOSTS` supaya bukan open proxy —
  **jangan longgarkan** batasan itu.
- **Kartu list bisa "lebih maju" dari halaman detail** (mengiklankan chapter
  yang belum live). Perbandingan pakai **nomor chapter**; kalau scrape menambah
  0 chapter, anggap belum berubah.
- **URL reader dibangun dari `request.base_url`** (main.py `read_chapter`).
  Di balik reverse proxy, uvicorn butuh `--proxy-headers`/`--forwarded-allow-ips`
  + proxy kirim `X-Forwarded-Proto/Host`, kalau tidak URL `/img` salah host.

## Tugas umum → mulai dari mana

- Tambah/ubah field manga → `db.py` (model) + `scraper.scrape_detail` (parse) +
  `ingest.upsert_manga` (simpan) + schema respons di `main.py`.
- Tambah endpoint → `main.py` (pakai `Depends(get_db)` untuk session).
- Ubah logika "chapter baru" → `get_new/worker.py` (`_check_card`).
- Ubah cara crawl massal → `crawl_catalog.py` / `enrich_details.py`.

## Uji cepat setelah perubahan

```bash
python run.py --api-only      # nyalakan API saja
curl "http://127.0.0.1:8080/manga?limit=1"
```

Worker bisa dites tanpa loop: `python get_new/worker.py --once`.
