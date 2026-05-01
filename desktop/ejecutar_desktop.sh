#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "Iniciando DocPresupuestoAI Escritorio..."

python3 -c "import fastapi,uvicorn,openai,anthropic,pdfplumber,docx,reportlab,openpyxl,sqlalchemy,webview" 2>/dev/null || {
  echo "Instalando dependencias necesarias..."
  pip3 install fastapi uvicorn python-multipart openai anthropic pdfplumber python-docx reportlab openpyxl Pillow sqlalchemy aiofiles jinja2 -q
  pip3 install -r desktop/requirements-desktop.txt -q
}

python3 desktop/app_desktop.py
