# get_new — Worker Pengecek Chapter Terbaru

Worker ini memantau update terbaru dari Komiku dan menambahkan chapter baru
ke database `komiku_api/komiku.db` (dipakai bareng oleh `komiku_api`).

## Cara kerja

1. Ambil daftar "update terbaru" dari endpoint htmx yang mengisi
   `<div class="daftar">` di <https://komiku.org/pustaka/>:
   - `https://api.komiku.org/manga/` (halaman 1)
   - `https://api.komiku.org/manga/page/N/` (halaman berikutnya)

   Daftar ini terurut dari yang **paling baru** di-update.
2. Tiap kartu `.bge` berisi link manga (`.bgei a[href]`) dan blok `.new1`
   **"Terbaru:"** yang menunjuk chapter paling akhir.
3. Bandingkan dengan DB:
   - Manga ada, chapter terbaru **belum** tercatat → scrape halaman detail
     lalu `upsert` (chapter baru otomatis ditambah, idempoten by URL).
   - Manga **belum** ada → ingest detail penuh (manga baru).
   - Manga ada & chapter terbaru sudah tercatat → dilewati.
4. Worker **menyusuri halaman demi halaman** (1, 2, 3, ...), tidak berhenti
   di page 1. Berhenti setelah menemukan **`--stop-after` kartu beruntun**
   (default **30**) yang chapternya sudah ada semua di DB. Counter beruntun
   **direset tiap ada perubahan**, jadi kalau di page dalam masih ada update,
   worker lanjut lebih dalam. `--max-pages` hanya batas pengaman.

Catatan: kadang kartu di list Komiku "lebih maju" dari halaman detailnya
(mengiklankan chapter yang belum live). Perbandingan pakai **nomor chapter**;
kalau scrape ternyata menambah 0 chapter, dianggap belum berubah (tidak
mereset streak, ditandai `~ ... belum live`).

Logika scrape & upsert memakai ulang modul di `komiku_api/`
(`scraper.py`, `ingest.py`, `db.py`) supaya konsisten.

## Menjalankan

Butuh Python 3.13 yang punya `scrapling` (sama seperti komiku_api).

```bash
# sekali jalan (instan): susuri page 1,2,3,... sampai 30 kartu beruntun
# sudah ada di DB, lalu keluar
python worker.py --once

# loop tiap 30 menit (default): tiap siklus juga susuri sampai 30 beruntun
python worker.py

# loop tiap 15 menit, berhenti setelah 50 kartu beruntun sudah ada
python worker.py --interval 900 --stop-after 50
```

Di Windows bisa pakai `run.bat` (double-click atau dari terminal), mis:
`run.bat --once`.

## Opsi

| Flag            | Default | Keterangan                                                      |
|-----------------|---------|----------------------------------------------------------------|
| `--once`        | off     | Jalan sekali lalu keluar (mode instan)                         |
| `--interval N`  | `1800`  | Jeda antar siklus (detik). 1800 = 30 menit                     |
| `--stop-after N`| `30`    | Berhenti setelah N kartu beruntun sudah ada di DB. 0 = sampai `--max-pages` |
| `--max-pages N` | `100`   | Batas pengaman jumlah halaman per siklus                        |
| `--delay N`     | `1.0`   | Jeda antar halaman (detik)                                      |

## Catatan

- DB yang dipakai selalu `komiku_api/komiku.db` (path absolut), tidak
  bergantung pada direktori tempat worker dijalankan.
- Aman dijalankan berulang: penambahan chapter idempoten (by URL chapter),
  jadi tidak akan ada duplikat.

## Produksi

> Untuk menyalakan worker **bersama** API dengan 1 perintah, pakai launcher di
> root: `run.bat` / `python run.py` (lihat `../README.md`). Bagian ini soal
> detail produksi khusus worker-nya.

### Menjalankan

Di produksi worker jalan **loop** (bukan `--once`). Lewat launcher root:

```bash
run.bat --worker-only
```

Interval & agresivitas diatur lewat env (dibaca launcher) atau flag langsung:

- `WORKER_INTERVAL` (env, dipakai launcher) atau `--interval N` — jeda antar
  siklus. Default `1800` (30 menit). Naikkan kalau tak mau sering nembak Komiku.
- `--stop-after N` — berhenti tiap siklus setelah N kartu beruntun sudah ada di
  DB (default 30). Makin kecil = siklus makin cepat selesai, tapi bisa lewatkan
  update yang "terkubur" di halaman dalam.
- `--delay N` — jeda antar halaman (default 1.0 dtk). **Jangan diturunkan
  agresif** — ini sopan-santun ke server Komiku, hindari rate-limit/ban.

### Aturan penting

- **Satu instance saja per DB.** Jangan jalankan dua worker menunjuk
  `komiku_api/komiku.db` yang sama — pemborosan request dan menambah kontensi
  tulis SQLite. Launcher root sudah menjaga hanya satu worker.
- **Aktifkan WAL** pada `komiku.db` (lihat `komiku_api/README.md` → Produksi)
  supaya tulis worker tidak sering bentrok dengan baca API
  (`database is locked`).
- **Idempoten & resumable.** Aman di-stop/kill kapan saja; siklus berikutnya
  melanjutkan tanpa duplikat. Saat start, worker langsung menjalankan 1 siklus
  penuh lebih dulu baru masuk jeda.

### Logging & restart

- Worker menulis log ber-timestamp ke stdout (`flush=True`). Di bawah launcher
  root, log muncul dengan prefix `[worker]`. Arahkan stdout ke file bila perlu
  arsip: `run.bat --worker-only > worker.log 2>&1`.
- Kalau worker mati tak terduga, **launcher root me-restart otomatis**
  (backoff s/d 30 dtk). Kalau dijalankan sendiri tanpa launcher, bungkus dengan
  NSSM/Task Scheduler agar auto-restart.

### Beban ke Komiku

Tiap siklus menyusuri halaman "update terbaru" (1, 2, 3, ...) sampai `stop-after`
kartu beruntun sudah ada. Manga baru/updated memicu scrape halaman detail
(1 request tambahan per manga). Jaga `--interval` dan `--delay` wajar agar tidak
membebani Komiku.
