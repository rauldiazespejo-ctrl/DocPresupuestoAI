#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "==============================================="
echo " Diagnóstico local - DocPresupuestoAI"
echo "==============================================="
echo "Proyecto: $ROOT_DIR"
echo "Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

check_ok() { echo "✅ $1"; }
check_warn() { echo "⚠️  $1"; }
check_err() { echo "❌ $1"; }

echo "[1/6] Herramientas base"
if command -v python3 >/dev/null 2>&1; then
  check_ok "python3: $(python3 --version 2>&1)"
else
  check_err "python3 no encontrado"
fi

if command -v pip3 >/dev/null 2>&1; then
  check_ok "pip3 disponible"
else
  check_warn "pip3 no encontrado"
fi

echo ""
echo "[2/6] Archivos clave"
[[ -f "frontend/index.html" ]] && check_ok "frontend/index.html" || check_err "Falta frontend/index.html"
[[ -f "desktop/app_desktop.py" ]] && check_ok "desktop/app_desktop.py" || check_err "Falta desktop/app_desktop.py"
[[ -f "backend/main.py" ]] && check_ok "backend/main.py" || check_err "Falta backend/main.py"

echo ""
echo "[3/6] Dependencias Python críticas"
if python3 - <<'PY'
import importlib.util
mods = ["fastapi", "uvicorn", "webview", "sqlalchemy"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
if missing:
    print("MISSING:" + ",".join(missing))
    raise SystemExit(1)
print("OK")
PY
then
  check_ok "Dependencias críticas instaladas"
else
  check_warn "Faltan dependencias críticas (revisa salida anterior)"
fi

echo ""
echo "[4/6] Estado backend local (/health)"
if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
  check_ok "Backend responde en http://127.0.0.1:8000/health"
else
  check_warn "Backend no responde en /health (si está apagado, es esperable)"
fi

echo ""
echo "[5/6] Logs desktop"
DESKTOP_LOG="$HOME/Library/Logs/DocPresupuestoAI/desktop-launcher.log"
BACKEND_LOG="$HOME/Library/Logs/DocPresupuestoAI/backend.log"
[[ -f "$DESKTOP_LOG" ]] && check_ok "Desktop log: $DESKTOP_LOG" || check_warn "Sin desktop log aún"
[[ -f "$BACKEND_LOG" ]] && check_ok "Backend log: $BACKEND_LOG" || check_warn "Sin backend log aún"

echo ""
echo "[6/6] Estado git"
git status --short --branch

echo ""
echo "Diagnóstico finalizado."
