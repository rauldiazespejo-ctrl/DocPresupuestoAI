#!/bin/bash
# ════════════════════════════════════════════════════
#  DocPresupuestoAI - Script de inicio (navegador + backend)
# ════════════════════════════════════════════════════

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║         DocPresupuestoAI — Iniciando...          ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

if ! python3 -c "import fastapi, uvicorn, openai, anthropic, google.generativeai, pdfplumber, docx, reportlab, openpyxl, sqlalchemy, aiofiles, jinja2" 2>/dev/null; then
  echo "⚠️  Instalando dependencias desde requirements.txt..."
  pip3 install -r requirements.txt -q
fi

echo "🚀 Iniciando servidor backend en http://localhost:8000"
echo "🌐 Abriendo interfaz en el navegador..."
echo "💡 IA: Gemini/Groq gratis, Ollama local, DeepSeek/OpenAI/ZAI/Claude con API key (modal Configurar IA)."
echo ""
echo "Para detener el servidor presiona CTRL+C"
echo ""

(sleep 2 && open "http://127.0.0.1:8000/app/") &

exec python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
