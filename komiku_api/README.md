# Komiku API

Scraper (Scrapling) + database + REST API (FastAPI) untuk katalog manga Komiku.

## Struktur

```
komiku_api/
├── scraper.py         # scrape_list/detail/chapter + fetch_image -> data terstruktur
├── schema.sql         # skema SQL murni (SQLite; catatan Postgres di dalam)
├── db.py              # model SQLAlchemy 2.0 + engine/session
├── ingest.py          # scrape 1 URL -> upsert ke DB (idempoten)
├── crawl_catalog.py   # TAHAP 1: crawl semua halaman katalog (level kartu)
├── enrich_details.py  # TAHAP 2: isi detail manga yang belum lengkap
├── bulk_ingest.py     # 1 halaman daftar + langsung detail (sampel cepat)
├── main.py            # FastAPI app
├── requirements.txt
└── komiku.db          # dibuat otomatis
```

## Skema data

```
manga ──< manga_genre >── genre        (many-to-many)
  │
  └──< chapter                          (one-to-many)
```

| Tabel     | Isi                                                                 |
|-----------|---------------------------------------------------------------------|
| `manga`   | slug, title, title_alt, type, theme, author, status, age_rating, reading_direction, total_views, synopsis, thumbnail, source_url |
| `genre`   | name (unik)                                                         |
| `manga_genre` | relasi m2m manga↔genre                                          |
| `chapter` | manga_id, name, number, url, released_at                            |

> Catatan: field **"Rating: 15+"** di Komiku adalah *content/age rating*, bukan skor numerik — disimpan di `age_rating`. Halaman detail tidak punya skor bintang.

## Cara pakai

Install:

```bash
pip install -r requirements.txt
scrapling install
```

Isi DB (scrape 1 manga):

```bash
python ingest.py https://komiku.org/manga/50kg-cinderella/
```

Jalankan API:

```bash
uvicorn main:app --reload --port 8080
```

Buka docs interaktif: http://127.0.0.1:8080/docs

## Endpoint

| Method | Path                        | Fungsi                                        |
|--------|-----------------------------|-----------------------------------------------|
| GET    | `/manga`                    | list + filter `q`, `genre`, `status`, `type`, paging `skip`/`limit` |
| GET    | `/manga/{slug}`             | detail lengkap + genres + chapters            |
| GET    | `/manga/{slug}/chapters`    | daftar chapter (urut naik)                    |
| GET    | `/manga/{slug}/chapter/{number}` | halaman baca — **live scrape**, tidak baca DB |
| GET    | `/img?url=`                 | proxy byte gambar (pasang Referer, lolos hotlink) |
| GET    | `/genres`                   | daftar genre + jumlah manga                   |
| POST   | `/ingest`                   | `{"url": "..."}` → scrape+simpan di background |

### Reader chapter (live)

Konsepnya seperti `axios` + `cheerio` di Node: **tidak ada URL gambar yang
disimpan**. Saat request masuk, backend yang fetch halaman Komiku, parse
`#Baca_Komik img.ww`, lalu balikan hasilnya.

```
GET /manga/50kg-cinderella/chapter/1.1
        │
        ├─ resolve URL chapter  → https://komiku.org/50kg-cinderella-chapter-1-1/
        ├─ fetch halaman        (scrapling Fetcher ≈ axios)
        ├─ parse #Baca_Komik img.ww   (selector ≈ cheerio)
        └─ balikan images → /img?url=... (byte gambar lewat backend)
```

```json
{ "slug": "manga/50kg-cinderella/chapter/1.1", "image_count": 39,
  "source_url": "https://komiku.org/50kg-cinderella-chapter-1-1/",
  "images": ["http://127.0.0.1:8080/img?url=https%3A%2F%2Fimg.komiku.org%2F..."] }
```

Query param:

| Param | Efek |
|-------|------|
| *(default)* | `images` menunjuk `/img?url=...` → bisa langsung dipakai `<img src>` |
| `?raw=true` | URL asli CDN Komiku (client harus kirim `Referer` sendiri) |
| `?proxy=https://worker.dev` | bungkus lewat proxy eksternal |
| `?fresh=true` | abaikan cache, fetch ulang ke Komiku |

Halaman chapter yang sudah diparse ditahan **di memori** selama 5 menit
(`_CHAPTER_TTL` di `main.py`) supaya reload tidak nembak Komiku berulang.
Hilang saat restart — ini cache, bukan penyimpanan.

> **Kenapa perlu `/img`.** `img.komiku.org` punya hotlink protection: request
> tanpa `Referer` komiku.org dibalas **403 + HTML ±4,9 KB** (bukan gambar), dengan
> `Referer: https://komiku.org/` → **200 `image/jpeg`**. Jadi URL asli tidak bisa
> dipasang langsung di `<img>` dari domain lain. Endpoint `/img` yang memasang
> header itu di sisi server.
>
> `/img` dibatasi ke host CDN Komiku (`scraper.IMAGE_HOSTS`) supaya tidak jadi
> **open proxy** — tanpa batasan itu siapa pun bisa memakai server ini untuk
> menembak URL sembarangan, termasuk alamat internal.

> **Gambar tidak disimpan di DB.** Tabel `chapter_image` sudah dibuang; tidak
> ada URL gambar di database. Semua gambar diambil live saat request masuk.

Contoh detail response:

```json
{
  "slug": "50kg-cinderella",
  "title": "50kg Cinderella",
  "type": "Manga", "theme": "Drama",
  "author": "Jung Min-a", "status": "Ongoing", "age_rating": "15+",
  "genres": ["Drama", "Josei", "Romance", "Slice of Life"],
  "thumbnail": "https://thumbnail.komiku.org/uploads/manga/50kg-cinderella/manga_thumbnail-50kg-Cinderella-Cover.jpg?w=500",
  "chapters": [{"name": "Chapter 1.1", "number": 1.1, "url": "...", "released_at": "07/09/2022"}]
}
```

## Crawl seluruh katalog / semua title (2 tahap)

### Paginasi Komiku

Parameternya **`halaman`**, bukan `page` — `?page=2` diabaikan dan diam-diam
mengembalikan halaman 1 lagi. Halaman 1 tidak perlu parameter. 50 kartu/halaman.

```
https://komiku.org/daftar-komik/                        -> halaman 1, semua tipe
https://komiku.org/daftar-komik/?halaman=2              -> halaman 2, semua tipe
https://komiku.org/daftar-komik/?tipe=manga&halaman=3   -> halaman 3, tipe manga
```

Jumlah halaman per tipe (diverifikasi 28 Jul 2026 dengan menembak halaman
terakhir + 1):

| Filter | Halaman terakhir | Kartu di halaman terakhir | Perkiraan judul |
|--------|------------------|---------------------------|-----------------|
| `?tipe=manga`  | **82**  | 13 | ~4.063 |
| `?tipe=manhwa` | **35**  |  3 | ~1.703 |
| `?tipe=manhua` | **37**  |  4 | ~1.804 |
| *(tanpa filter)* | **152** | 16 | ~7.566 |

> **Jangan percaya widget paginasi sebagai penanda akhir.** Halaman di luar
> batas tetap membalas **HTTP 200** dengan body normal, cuma tanpa `.manga-card`
> — bukan 404. Jadi patokan berhenti yang benar adalah **jumlah kartu = 0**,
> bukan status code. `crawl_catalog.py` sudah pakai aturan ini.

### Tahap 1 — katalog (cepat, 1 request per halaman)

Simpan data level-kartu (title, slug, href, thumbnail, tipe, status) untuk
semua judul. Berhenti otomatis saat sebuah halaman mengembalikan 0 kartu.

```bash
python crawl_catalog.py --tipe manga --delay 0.5    # ~82 request
python crawl_catalog.py --tipe manhwa --delay 0.5   # ~35 request
python crawl_catalog.py --tipe manhua --delay 0.5   # ~37 request
python crawl_catalog.py --tipe "" --delay 0.5       # semua tipe sekaligus, ~152 request
```

| Flag | Arti |
|------|------|
| `--tipe` | `manga` / `manhwa` / `manhua`; string kosong = tanpa filter (default `manga`) |
| `--max` | batas halaman sebagai pengaman (default 200) — bukan target, cuma rem darurat |
| `--delay` | jeda detik antar halaman (default 0.5) |

Output per halaman berisi jumlah kartu, berapa yang baru, dan kumulatif unik:

```
halaman   1: 50 kartu (50 baru)  | kumulatif unik=50
halaman   2: 50 kartu (12 baru)  | kumulatif unik=100
...
halaman  82: 13 kartu (2 baru)   | kumulatif unik=4063
halaman  83: 0 kartu -> selesai
```

### Tahap 2 — detail (resumable, berat)

Isi author, sinopsis, genre, dan daftar chapter untuk manga yang belum
didetailkan (`synopsis IS NULL`). Aman di-stop/di-ulang kapan saja.

```bash
python enrich_details.py --limit 300 --delay 0.6   # sebagian
python enrich_details.py --delay 0.6               # semua sisanya (~1-2 jam)
```

> Penanda progres = `synopsis IS NULL`. Manga yang sudah detail otomatis dilewati,
> jadi Tahap 2 boleh dijalankan berkali-kali sampai habis.

### bulk_ingest.py (1 halaman + langsung detail)

`python bulk_ingest.py` — ambil 1 halaman daftar (50 manga) lalu langsung
scrape detail tiap-tiapnya. Cocok untuk sampel cepat.

### Anti-scrape-ulang (dedup)

Semua scraper melewati manga yang sudah pernah diambil, jadi aman dijalankan
berkali-kali (mis. judul sama muncul di page 1 dan page 2):

| Script | Cara skip |
|--------|-----------|
| `crawl_catalog.py` | `seen_slugs` per run + `upsert_card` idempoten by slug |
| `bulk_ingest.py`   | dedup dalam-run (slug/url) **+** cek DB `is_detailed()` |
| `enrich_details.py`| hanya proses `synopsis IS NULL` (belum didetailkan) |

Penanda "sudah detail" = kolom `synopsis` terisi. Untuk memaksa scrape ulang:
`python bulk_ingest.py --force`.

### Cek progres

```bash
python -c "import sqlite3; c=sqlite3.connect('komiku.db'); q=lambda s: c.execute(s).fetchone()[0]; print('manga    :', q('select count(*) from manga')); print('didetail :', q('select count(*) from manga where synopsis is not null')); print('chapter  :', q('select count(*) from chapter'))"
```

Status per 28 Jul 2026: **4.073 manga** di katalog, **90** sudah didetailkan,
**2.647 chapter**. Sisanya tinggal jalankan Tahap 2 sampai habis.

## Produksi

> Untuk menyalakan API **bersama** worker `get_new` dengan 1 perintah, pakai
> launcher di root: `run.bat` / `python run.py` (lihat `../README.md`).
> Bagian ini soal detail produksi khusus API-nya.

### Menjalankan

Jangan pakai `--reload` di produksi (itu untuk dev). Contoh:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

Atau lewat launcher root (default host `0.0.0.0`, port `8080`):

```bash
run.bat --api-only
```

**Workers.** Endpoint API sebagian besar baca DB; reader chapter live-fetch ke
Komiku (I/O-bound). Boleh menaikkan `--workers N` untuk paralelisme, tapi:

- Cache halaman chapter (`_chapter_cache` di `main.py`) **per-proses** — dengan
  banyak worker, hit-rate cache turun (tetap benar, cuma lebih sering nembak
  Komiku). Kalau butuh cache lintas-proses, pindah ke Redis dsb.
- `--workers` tidak bisa dipakai bareng `--reload`.

### Di balik reverse proxy (PENTING)

Endpoint reader (`/manga/{slug}/chapter/{number}`) membangun URL `/img?url=...`
dari **`request.base_url`**. Di balik nginx/Caddy, kalau header forwarded tidak
diteruskan, URL gambar akan salah (mis. `http://127.0.0.1:8080/...` alih-alih
`https://domainmu/...`).

- Jalankan uvicorn dengan `--proxy-headers --forwarded-allow-ips="*"`
  (atau IP proxy yang spesifik).
- Proxy harus mengirim `X-Forwarded-Proto` dan `X-Forwarded-Host`.

Contoh:

```bash
uvicorn main:app --host 127.0.0.1 --port 8080 --proxy-headers --forwarded-allow-ips="*"
```

### Database (SQLite)

- Path DB sudah **absolut** (`db.py` → `komiku_api/komiku.db`), jadi API selalu
  memakai DB yang benar tak peduli dari direktori mana dijalankan.
- API (baca) berjalan bareng worker (tulis) di file yang sama. Untuk mengurangi
  error `database is locked` saat trafik naik, **aktifkan mode WAL** sekali saja:

  ```bash
  python -c "import sqlite3; c=sqlite3.connect('komiku.db'); print(c.execute('PRAGMA journal_mode=WAL').fetchone()); c.close()"
  ```

  (WAL itu setting persisten di file DB; cukup dijalankan sekali.)
- **Backup** = cukup salin `komiku.db` saat proses idle, atau
  `sqlite3 komiku.db ".backup komiku-backup.db"` (aman selagi berjalan).
- Bersihkan artefak yang tidak dipakai di produksi: `komiku - Copy.db`,
  `komiku.db.bak`.

### `/img` sebagai open-proxy guard

`/img` sengaja dibatasi ke `scraper.IMAGE_HOSTS` (CDN gambar Komiku). Jangan
longgarkan — tanpa batas itu server bisa dipakai orang untuk menembak URL
sembarangan (termasuk alamat internal). Set `Cache-Control` sudah 1 hari.

### Sebagai service Windows

Bungkus launcher root dengan **NSSM** atau **Task Scheduler** (trigger "At
startup", restart on failure). Launcher sudah menangani restart worker; service
manager yang menangani restart seluruh launcher kalau API mati.
