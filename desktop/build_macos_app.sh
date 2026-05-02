#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="DocPresupuestoAI"
APP_VERSION="${1:-1.0.0}"
BUNDLE_ID="cl.pulsoai.docpresupuestoai"
DISPLAY_NAME="DocPresupuestoAI"
DEVELOPER_NAME="Pulso AI"
APP_PATH="dist/${APP_NAME}.app"
DMG_PATH="dist/${APP_NAME}-${APP_VERSION}.dmg"

echo "Generando app macOS (.app) de ${APP_NAME}..."
echo "Version: ${APP_VERSION}"
echo "Developer: ${DEVELOPER_NAME}"

python3 -m pip install pyinstaller -q
python3 -m pip install -r requirements.txt -q
python3 -m pip install -r desktop/requirements-desktop.txt -q

pyinstaller \
  --noconfirm \
  --windowed \
  --name "${APP_NAME}" \
  --osx-bundle-identifier "${BUNDLE_ID}" \
  --paths "$ROOT_DIR" \
  --add-data "$ROOT_DIR/frontend:frontend" \
  --add-data "$ROOT_DIR/backend:backend" \
  --add-data "$ROOT_DIR/database:database" \
  --add-data "$ROOT_DIR/templates:templates" \
  --add-data "$ROOT_DIR/docs:docs" \
  --hidden-import=backend.main \
  --collect-all=uvicorn \
  --collect-all=fastapi \
  --collect-all=starlette \
  --hidden-import=google.generativeai \
  --collect-all=google.generativeai \
  "$ROOT_DIR/desktop/app_desktop.py"

PLIST_PATH="${APP_PATH}/Contents/Info.plist"
if [ -f "${PLIST_PATH}" ]; then
  /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier ${BUNDLE_ID}" "${PLIST_PATH}" || true
  /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName ${DISPLAY_NAME}" "${PLIST_PATH}" || true
  /usr/libexec/PlistBuddy -c "Set :CFBundleName ${DISPLAY_NAME}" "${PLIST_PATH}" || true
  /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString ${APP_VERSION}" "${PLIST_PATH}" || true
  /usr/libexec/PlistBuddy -c "Set :CFBundleVersion ${APP_VERSION}" "${PLIST_PATH}" || /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string ${APP_VERSION}" "${PLIST_PATH}"
  /usr/libexec/PlistBuddy -c "Set :NSHumanReadableCopyright © Pulso AI" "${PLIST_PATH}" || /usr/libexec/PlistBuddy -c "Add :NSHumanReadableCopyright string © Pulso AI" "${PLIST_PATH}"
  /usr/libexec/PlistBuddy -c "Set :CFBundleGetInfoString ${DISPLAY_NAME} ${APP_VERSION} by ${DEVELOPER_NAME}" "${PLIST_PATH}" || /usr/libexec/PlistBuddy -c "Add :CFBundleGetInfoString string ${DISPLAY_NAME} ${APP_VERSION} by ${DEVELOPER_NAME}" "${PLIST_PATH}"
fi

# Ad-hoc signing for smoother local execution tests.
codesign --force --deep --sign - "${APP_PATH}" >/dev/null 2>&1 || true

# Build DMG installer image
rm -f "${DMG_PATH}"
hdiutil create -volname "${DISPLAY_NAME}" -srcfolder "${APP_PATH}" -ov -format UDZO "${DMG_PATH}" >/dev/null

echo ""
echo "Listo: ${APP_PATH}"
echo "Instalador DMG: ${DMG_PATH}"
echo "Nota: la UI se carga desde http://127.0.0.1:8000/app/ (frontend del bundle); reconstruye tras cambiar index.html."
