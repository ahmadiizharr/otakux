#!/usr/bin/env python3
"""
Satu perintah untuk menjalankan seluruh aplikasi Komiku:

  * API    -> komiku_api  (FastAPI/uvicorn) di http://HOST:PORT
  * Worker -> get_new     (pengecek chapter terbaru, loop tiap WORKER_INTERVAL)

Keduanya memakai database yang sama: komiku_api/komiku.db (SQLite, tanpa
server terpisah).

Pemakaian:
    python run.py                # jalankan API + worker (default)
    python run.py --api-only     # API saja
    python run.py --worker-only  # worker saja

Konfigurasi lewat environment variable:
    HOST             host uvicorn        (default 0.0.0.0)
    PORT             port uvicorn        (default 8080)
    WORKER_INTERVAL  detik antar siklus worker (default 1800 = 30 menit)
    RELOAD           set '1' untuk uvicorn --reload (mode dev)

Ctrl+C menghentikan semuanya. Kalau API mati, seluruh launcher berhenti;
kalau worker mati, worker di-restart otomatis (dengan backoff).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KOMIKU_DIR = ROOT / "komiku_api"
WORKER_DIR = ROOT / "get_new"
PY = sys.executable  # interpreter yang sama dipakai untuk kedua service

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = os.environ.get("PORT", "8080")
WORKER_INTERVAL = os.environ.get("WORKER_INTERVAL", "1800")
RELOAD = os.environ.get("RELOAD", "") not in ("", "0", "false", "False")

# Anak proses: output tak dibuffer + UTF-8 supaya log rapi & real-time.
CHILD_ENV = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}


def _api_cmd() -> list[str]:
    cmd = [PY, "-m", "uvicorn", "main:app", "--host", HOST, "--port", PORT]
    if RELOAD:
        cmd.append("--reload")
    return cmd


def _worker_cmd() -> list[str]:
    return [PY, "worker.py", "--interval", WORKER_INTERVAL]


def _pump(proc: subprocess.Popen, prefix: str) -> None:
    """Teruskan output child ke stdout launcher dengan prefix [nama]."""
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        print(f"{prefix} {line}", flush=True)


class Service:
    """Satu service (API/worker): spawn, tampilkan log, restart bila perlu."""

    def __init__(self, name: str, cmd: list[str], cwd: Path, restart: bool):
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.restart = restart          # True untuk worker (loop abadi)
        self.proc: subprocess.Popen | None = None

    def run(self, stop: threading.Event) -> None:
        backoff = 1.0
        while not stop.is_set():
            try:
                proc = subprocess.Popen(
                    self.cmd, cwd=str(self.cwd),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    env=CHILD_ENV,
                )
            except Exception as e:  # noqa: BLE001
                print(f"[run] gagal start '{self.name}': {e}", flush=True)
                stop.set()
                return
            self.proc = proc
            pump = threading.Thread(
                target=_pump, args=(proc, f"[{self.name}]"), daemon=True)
            pump.start()
            proc.wait()
            pump.join(timeout=2)

            if stop.is_set():
                return
            code = proc.returncode
            if not self.restart:
                # API mati = fatal -> matikan semuanya.
                print(f"[run] '{self.name}' berhenti (exit {code}) "
                      f"-> mematikan semua.", flush=True)
                stop.set()
                return
            # Worker harusnya jalan terus; kalau keluar, restart dgn backoff.
            print(f"[run] '{self.name}' berhenti (exit {code}) "
                  f"-> restart dalam {backoff:.0f}s", flush=True)
            if stop.wait(backoff):
                return
            backoff = min(backoff * 2, 30)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Launcher 1-perintah: API (komiku_api) + worker (get_new)")
    ap.add_argument("--api-only", action="store_true",
                    help="jalankan API saja")
    ap.add_argument("--worker-only", action="store_true",
                    help="jalankan worker saja")
    args = ap.parse_args()

    if args.api_only and args.worker_only:
        ap.error("--api-only dan --worker-only tidak bisa dipakai bersamaan")

    services: list[Service] = []
    if not args.worker_only:
        print(f"[run] API    -> http://{HOST}:{PORT}  (docs: /docs)"
              + ("  [reload]" if RELOAD else ""), flush=True)
        services.append(Service("api", _api_cmd(), KOMIKU_DIR, restart=False))
    if not args.api_only:
        print(f"[run] Worker -> cek chapter terbaru tiap {WORKER_INTERVAL}s",
              flush=True)
        services.append(Service("worker", _worker_cmd(), WORKER_DIR, restart=True))

    print("[run] Ctrl+C untuk berhenti.\n", flush=True)

    stop = threading.Event()
    threads = [threading.Thread(target=s.run, args=(stop,), daemon=True)
               for s in services]
    for t in threads:
        t.start()

    try:
        while not stop.is_set() and any(t.is_alive() for t in threads):
            stop.wait(0.5)
    except KeyboardInterrupt:
        print("\n[run] Ctrl+C -> menghentikan semua service...", flush=True)
    finally:
        stop.set()
        for s in services:                      # minta berhenti (SIGTERM)
            p = s.proc
            if p and p.poll() is None:
                try:
                    p.terminate()
                except Exception:               # noqa: BLE001
                    pass
        deadline = time.time() + 10             # tunggu, lalu paksa kill
        for s in services:
            p = s.proc
            if not p:
                continue
            try:
                p.wait(timeout=max(0.0, deadline - time.time()))
            except Exception:                   # noqa: BLE001
                try:
                    p.kill()
                except Exception:               # noqa: BLE001
                    pass
        for t in threads:
            t.join(timeout=2)

    print("[run] selesai.", flush=True)


if __name__ == "__main__":
    main()
