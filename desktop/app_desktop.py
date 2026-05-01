#!/usr/bin/env python3
"""
DocPresupuestoAI desktop launcher (macOS-friendly).

Starts the FastAPI backend and opens the existing frontend in a native window
using pywebview. Intended for pilot testing on desktop.
"""

from __future__ import annotations

import atexit
import fcntl
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import webview


APP_NAME = "DocPresupuestoAI"
DEVELOPER_NAME = "Pulso AI"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
HEALTH_URL = f"{BACKEND_URL}/health"


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[1]


ROOT = _project_root()
FRONTEND_FILE = ROOT / "frontend" / "index.html"
_backend_process: subprocess.Popen | None = None
_instance_lock_handle = None
LOCK_FILE_PATH = Path("/tmp/docpresupuestoai.lock")


def _wait_backend_ready(timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.4)
    return False


def _start_backend() -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        BACKEND_HOST,
        "--port",
        str(BACKEND_PORT),
    ]
    return subprocess.Popen(command, cwd=str(ROOT), env=env)


def _stop_backend() -> None:
    global _backend_process
    if _backend_process is None:
        return
    if _backend_process.poll() is None:
        _backend_process.terminate()
        try:
            _backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _backend_process.kill()
    _backend_process = None


def _handle_exit_signal(signum, _frame) -> None:
    _stop_backend()
    raise SystemExit(0 if signum in (signal.SIGINT, signal.SIGTERM) else 1)


def _acquire_single_instance_lock() -> bool:
    """
    Prevent multiple desktop windows from launching at once.
    This avoids accidental mass openings after install or double-click bursts.
    """
    global _instance_lock_handle
    LOCK_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _instance_lock_handle = open(LOCK_FILE_PATH, "w")
    try:
        fcntl.flock(_instance_lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _instance_lock_handle.write(str(os.getpid()))
        _instance_lock_handle.flush()
        return True
    except BlockingIOError:
        return False


def main() -> int:
    global _backend_process

    if not _acquire_single_instance_lock():
        print("DocPresupuestoAI ya está en ejecución. Se evita abrir otra instancia.")
        return 0

    if not FRONTEND_FILE.exists():
        print(f"Frontend no encontrado: {FRONTEND_FILE}")
        return 1

    signal.signal(signal.SIGINT, _handle_exit_signal)
    signal.signal(signal.SIGTERM, _handle_exit_signal)
    atexit.register(_stop_backend)

    _backend_process = _start_backend()
    if not _wait_backend_ready():
        print("No fue posible iniciar backend en /health.")
        _stop_backend()
        return 1

    window_url = FRONTEND_FILE.resolve().as_uri()
    webview.create_window(
        f"{APP_NAME} - Escritorio | Desarrollado por {DEVELOPER_NAME}",
        window_url,
        width=1440,
        height=900,
        min_size=(1180, 760),
    )
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
