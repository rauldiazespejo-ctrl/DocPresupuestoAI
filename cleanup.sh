#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

KEEP_LOCAL_CONFIG="frontend/local-config.js"
EXAMPLE_LOCAL_CONFIG="frontend/local-config.example.js"
TMP_LOCAL_CONFIG_BACKUP=""

MODE="${1:-run}"

echo "🧹 DocPresupuestoAI Cleanup"
echo "Directorio: $ROOT_DIR"
echo ""

if [[ "$MODE" == "--dry-run" ]]; then
  echo "Modo simulación: se mostrarán archivos a eliminar."
  git clean -ndX
  if [[ -f "$KEEP_LOCAL_CONFIG" ]]; then
    echo ""
    echo "Nota: $KEEP_LOCAL_CONFIG será respaldado y restaurado automáticamente."
  fi
  exit 0
fi

if [[ "$MODE" == "--help" ]]; then
  echo "Uso:"
  echo "  ./cleanup.sh           Limpia artefactos ignorados"
  echo "  ./cleanup.sh --dry-run Muestra qué se eliminaría"
  exit 0
fi

echo "Eliminando artefactos ignorados (build/cache/temp)..."
if [[ -f "$KEEP_LOCAL_CONFIG" ]]; then
  TMP_LOCAL_CONFIG_BACKUP="$(mktemp)"
  cp "$KEEP_LOCAL_CONFIG" "$TMP_LOCAL_CONFIG_BACKUP"
fi

git clean -fdX

if [[ -n "$TMP_LOCAL_CONFIG_BACKUP" && -f "$TMP_LOCAL_CONFIG_BACKUP" ]]; then
  mkdir -p "$(dirname "$KEEP_LOCAL_CONFIG")"
  cp "$TMP_LOCAL_CONFIG_BACKUP" "$KEEP_LOCAL_CONFIG"
  rm -f "$TMP_LOCAL_CONFIG_BACKUP"
fi

if [[ ! -f "$KEEP_LOCAL_CONFIG" && -f "$EXAMPLE_LOCAL_CONFIG" ]]; then
  echo "Recreando $KEEP_LOCAL_CONFIG desde ejemplo..."
  cp "$EXAMPLE_LOCAL_CONFIG" "$KEEP_LOCAL_CONFIG"
fi

echo ""
echo "✅ Limpieza finalizada"
git status --short --branch
