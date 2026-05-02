#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR"

echo "DocPresupuestoAI — Escritorio"
echo "Ollama: deja «ollama serve» activo; en Configurar IA elige Ollama y clave vacía (opcional: OLLAMA_BASE_URL, por defecto http://127.0.0.1:11434/v1)."
echo ""

if ! python3 -c "import fastapi, uvicorn, openai, anthropic, google.generativeai, pdfplumber, docx, reportlab, openpyxl, sqlalchemy, aiofiles, jinja2, webview" 2>/dev/null; then
  echo "Instalando dependencias desde requirements.txt y escritorio..."
  pip3 install -r requirements.txt -q
  pip3 install -r desktop/requirements-desktop.txt -q
fi

exec python3 desktop/app_desktop.py
