# XIXI — Komiku

Dua service yang dulu dijalankan terpisah, sekarang **cukup 1 perintah**:

| Bagian        | Fungsi                                                    |
|---------------|-----------------------------------------------------------|
| `komiku_api/` | REST API (FastAPI) di atas database `komiku_api/komiku.db` |
| `get_new/`    | Worker yang loop mengecek chapter terbaru → tulis ke DB yang sama |

Database-nya SQLite (`komiku_api/komiku.db`) — **tidak ada server DB terpisah**
yang perlu dinyalakan. Cukup jalankan launcher.

## Menjalankan (1 perintah)

Windows:

```bash
run.bat
```

Atau lintas-platform:

```bash
python run.py
```

Ini menyalakan **API + worker** sekaligus. Log keduanya tampil dengan prefix
`[api]` dan `[worker]`. Tekan **Ctrl+C** untuk menghentikan semuanya.

- API: <http://localhost:8081> — docs interaktif: <http://localhost:8081/docs>
- Worker langsung mengecek update saat start, lalu ulang tiap 30 menit.

## Opsi

```bash
run.bat --api-only       # API saja
run.bat --worker-only    # worker saja
```

Konfigurasi lewat environment variable (opsional):

| Variabel          | Default   | Keterangan                             |
|-------------------|-----------|----------------------------------------|
| `HOST`            | `0.0.0.0` | host uvicorn                           |
| `PORT`            | `8081`    | port uvicorn                           |
| `WORKER_INTERVAL` | `1800`    | jeda antar siklus worker (detik)       |
| `RELOAD`          | *(off)*   | set `1` untuk `uvicorn --reload` (dev) |

Contoh (ganti port + interval worker 15 menit):

```bash
PORT=9000 WORKER_INTERVAL=900 python run.py
```

## Catatan produksi

- Kalau **API** mati, launcher ikut berhenti (dianggap fatal) supaya bisa
  di-restart oleh service manager (Task Scheduler / NSSM / systemd).
- Kalau **worker** mati, launcher me-restart-nya otomatis (backoff s/d 30s).
- Detail masing-masing service ada di `komiku_api/README.md` dan
  `get_new/README.md`.
