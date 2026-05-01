#!/bin/bash
# ════════════════════════════════════════════════════
#  DocPresupuestoAI - Script de inicio
# ════════════════════════════════════════════════════

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║         DocPresupuestoAI — Iniciando...          ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Verificar dependencias
python3 -c "import fastapi,uvicorn,openai,reportlab,sqlalchemy,pdfplumber,google.generativeai" 2>/dev/null
if [ $? -ne 0 ]; then
  echo "⚠️  Instalando dependencias..."
  pip3 install fastapi uvicorn python-multipart openai anthropic google-generativeai pdfplumber python-docx reportlab openpyxl Pillow sqlalchemy aiofiles jinja2 -q
fi

echo "🚀 Iniciando servidor backend en http://localhost:8000"
echo "🌐 Abriendo interfaz en el navegador..."
echo ""
echo "Para detener el servidor presiona CTRL+C"
echo ""

# Abrir navegador después de 2 segundos
(sleep 2 && open "$ROOT_DIR/frontend/index.html") &

# Iniciar servidor
cd "$ROOT_DIR" && PYTHONPATH="$ROOT_DIR" python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
