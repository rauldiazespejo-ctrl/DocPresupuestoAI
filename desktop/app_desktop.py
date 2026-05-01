#!/usr/bin/env python3
"""
DocPresupuestoAI desktop launcher (macOS-friendly).

Starts the FastAPI backend and opens the existing frontend in a native window
using pywebview. Intended for pilot testing on desktop.
"""

from __future__ import annotations

import atexit
from datetime import datetime
import fcntl
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

import uvicorn
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
_backend_process: Optional[subprocess.Popen] = None
_uvicorn_server: Any = None
_instance_lock_handle = None
_backend_log_handle = None
LOCK_FILE_PATH = Path("/tmp/docpresupuestoai.lock")
LOGS_DIR = Path.home() / "Library" / "Logs" / APP_NAME
DESKTOP_LOG_FILE = LOGS_DIR / "desktop-launcher.log"
BACKEND_LOG_FILE = LOGS_DIR / "backend.log"


def _log(message: str) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    with open(DESKTOP_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


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


def _is_stale_instance_lock() -> bool:
    try:
        raw = LOCK_FILE_PATH.read_text(encoding="utf-8").strip()
        pid = int(raw)
    except (OSError, ValueError):
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def _run_uvicorn_embedded() -> None:
    global _uvicorn_server

    config = uvicorn.Config(
        "backend.main:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    _uvicorn_server = server
    server.run()


def _start_backend() -> Optional[subprocess.Popen]:
    """
    En modo desarrollo: subprocess con el Python actual.
    En app empaquetada (PyInstaller): uvicorn en hilo daemon (sys.executable no es CPython).
    """
    global _backend_log_handle, _uvicorn_server

    if getattr(sys, "frozen", False):
        _log("Modo empaquetado: iniciando uvicorn en proceso (hilo daemon).")
        _uvicorn_server = None
        t = threading.Thread(target=_run_uvicorn_embedded, name="uvicorn-backend", daemon=True)
        t.start()
        time.sleep(0.35)
        return None

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
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    _backend_log_handle = open(BACKEND_LOG_FILE, "a", encoding="utf-8")
    _log(f"Iniciando backend: {' '.join(command)}")
    return subprocess.Popen(
        command,
        cwd=str(ROOT),
        env=env,
        stdout=_backend_log_handle,
        stderr=_backend_log_handle,
    )


def _stop_backend() -> None:
    global _backend_process, _backend_log_handle, _uvicorn_server

    if _uvicorn_server is not None:
        _log("Solicitando cierre del backend embebido (uvicorn)...")
        try:
            _uvicorn_server.should_exit = True
        except Exception as exc:
            _log(f"Aviso al detener uvicorn: {exc}")
        _uvicorn_server = None
        time.sleep(0.5)

    if _backend_process is None:
        if _backend_log_handle is not None:
            try:
                _backend_log_handle.close()
            except Exception:
                pass
            _backend_log_handle = None
        return
    if _backend_process.poll() is None:
        _log("Deteniendo proceso backend...")
        _backend_process.terminate()
        try:
            _backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _log("Backend no respondió a terminate; aplicando kill.")
            _backend_process.kill()
    else:
        _log(f"Backend ya detenido con código {_backend_process.returncode}.")
    _backend_process = None
    if _backend_log_handle is not None:
        try:
            _backend_log_handle.close()
        except Exception:
            pass
        _backend_log_handle = None


def _handle_exit_signal(signum, _frame) -> None:
    _stop_backend()
    raise SystemExit(0 if signum in (signal.SIGINT, signal.SIGTERM) else 1)


def _acquire_single_instance_lock() -> bool:
    """
    Evita múltiples ventanas; si el lock quedó huérfano (PID muerto), se libera una vez.
    """
    global _instance_lock_handle
    LOCK_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    for attempt in (0, 1):
        fh = open(LOCK_FILE_PATH, "w", encoding="utf-8")
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fh.close()
            if attempt == 0 and _is_stale_instance_lock():
                try:
                    os.unlink(LOCK_FILE_PATH)
                except OSError:
                    pass
                continue
            return False
        fh.write(str(os.getpid()))
        fh.flush()
        _instance_lock_handle = fh
        return True
    return False


def main() -> int:
    global _backend_process

    if not _acquire_single_instance_lock():
        _log("Intento bloqueado: ya existe una instancia activa.")
        print("DocPresupuestoAI ya está en ejecución. Se evita abrir otra instancia.")
        return 0

    if not FRONTEND_FILE.exists():
        _log(f"Frontend no encontrado en {FRONTEND_FILE}")
        print(f"Frontend no encontrado: {FRONTEND_FILE}")
        return 1

    signal.signal(signal.SIGINT, _handle_exit_signal)
    signal.signal(signal.SIGTERM, _handle_exit_signal)
    atexit.register(_stop_backend)

    _backend_process = _start_backend()
    if not _wait_backend_ready():
        _log("Fallo al iniciar backend: /health no respondió dentro del tiempo límite.")
        print("No fue posible iniciar backend en /health.")
        _stop_backend()
        return 1

    window_url = FRONTEND_FILE.resolve().as_uri()
    _log(f"Backend listo. Abriendo interfaz: {window_url}")
    try:
        webview.create_window(
            f"{APP_NAME} - Escritorio | Desarrollado por {DEVELOPER_NAME}",
            window_url,
            width=1440,
            height=900,
            min_size=(1180, 760),
        )
        webview.start()
    except Exception as exc:
        _log(f"Error en webview: {exc}")
        _stop_backend()
        print(f"Error al abrir interfaz desktop: {exc}")
        return 1
    _log("Aplicación cerrada por usuario.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
