#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/src/standalone_app.py"
OUT="$SCRIPT_DIR/dist/mac"
BUILD="$SCRIPT_DIR/build/mac"
APP_NAME="Offline-AI-Workstation"
DMG_NAME="Offline-AI-Workstation.dmg"
ICON="$SCRIPT_DIR/assets/app.icns"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
BOLD='\033[1m'

find_python() {
    local candidate
    for candidate in python3 python py; do
        if command -v "$candidate" >/dev/null 2>&1; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

add_data_if_present() {
    local source_path="$1"
    local target_name="$2"
    if [[ -e "$source_path" ]]; then
        PYINSTALLER_ARGS+=("--add-data" "$source_path:$target_name")
        echo -e "${GREEN}  [OK] Bundling $target_name from $source_path${NC}"
    else
        echo -e "${YELLOW}  [WARN] Missing optional bundle: $source_path${NC}"
    fi
}

PYTHON_BIN="$(find_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
    echo "Python 3.10+ is required to build the macOS app."
    exit 1
fi

if [[ ! -f "$SRC" ]]; then
    echo "Cannot find source file: $SRC"
    exit 1
fi

TARGET_ARCH="${MAC_TARGET_ARCH:-$(uname -m)}"
case "$TARGET_ARCH" in
    x86_64|arm64|universal2) ;;
    *)
        echo "Unsupported MAC_TARGET_ARCH: $TARGET_ARCH"
        echo "Use one of: x86_64, arm64, universal2"
        exit 1
        ;;
esac

echo ""
echo -e "${CYAN}${BOLD}== Building Offline AI Workstation for macOS ==${NC}"
echo "Using Python: $PYTHON_BIN"
echo "Target arch: $TARGET_ARCH"
echo ""

"$PYTHON_BIN" -m pip install --quiet --upgrade pyinstaller pillow pypdf certifi

mkdir -p "$OUT" "$BUILD"

PYINSTALLER_ARGS=(
    --noconfirm
    --onedir
    --windowed
    --name "$APP_NAME"
    --distpath "$OUT"
    --workpath "$BUILD"
    --specpath "$BUILD"
    --osx-bundle-identifier "com.offlineai.workstation"
    --target-arch "$TARGET_ARCH"
)

add_data_if_present "$SCRIPT_DIR/model-presets" "model-presets"
add_data_if_present "$SCRIPT_DIR/runtime-bin-mac" "runtime-bin-mac"
add_data_if_present "$SCRIPT_DIR/runtime-bin-darwin" "runtime-bin-darwin"
add_data_if_present "$SCRIPT_DIR/image-backend-bin-mac" "image-backend-bin-mac"
add_data_if_present "$SCRIPT_DIR/ocr-bin-mac" "ocr-bin-mac"

if [[ "${ALLOW_GENERIC_MAC_BUNDLES:-0}" == "1" ]]; then
    add_data_if_present "$SCRIPT_DIR/runtime-bin" "runtime-bin"
    add_data_if_present "$SCRIPT_DIR/image-backend-bin" "image-backend-bin"
    add_data_if_present "$SCRIPT_DIR/ocr-bin" "ocr-bin"
else
    echo -e "${YELLOW}  [WARN] Skipping generic runtime/image/OCR bundles by default on macOS.${NC}"
    echo -e "${YELLOW}        Set ALLOW_GENERIC_MAC_BUNDLES=1 if those folders contain mac-ready assets.${NC}"
fi

if [[ -f "$ICON" ]]; then
    PYINSTALLER_ARGS+=(--icon "$ICON")
    echo -e "${GREEN}  [OK] Using icon: $ICON${NC}"
else
    echo -e "${YELLOW}  [WARN] app.icns not found. Using default app icon.${NC}"
fi

"$PYTHON_BIN" -m PyInstaller "${PYINSTALLER_ARGS[@]}" "$SRC"

APP_PATH="$OUT/$APP_NAME.app"
if [[ ! -d "$APP_PATH" ]]; then
    echo "Build finished but app bundle was not created at $APP_PATH"
    exit 1
fi

echo ""
echo -e "${GREEN}  [OK] App bundle created: $APP_PATH${NC}"

if command -v create-dmg >/dev/null 2>&1; then
    echo "Creating DMG..."
    STAGING_DIR="$OUT/dmg-staging"
    rm -rf "$STAGING_DIR"
    mkdir -p "$STAGING_DIR"
    cp -R "$APP_PATH" "$STAGING_DIR/"

    create-dmg \
        --volname "Offline AI Workstation" \
        --window-pos 200 120 \
        --window-size 700 420 \
        --icon-size 100 \
        --icon "$APP_NAME.app" 180 190 \
        --app-drop-link 500 190 \
        --no-internet-enable \
        "$OUT/$DMG_NAME" \
        "$STAGING_DIR"

    rm -rf "$STAGING_DIR"
    echo -e "${GREEN}  [OK] DMG created: $OUT/$DMG_NAME${NC}"
else
    echo -e "${YELLOW}  [WARN] create-dmg not installed. Skipping DMG packaging.${NC}"
    echo "Zip the app instead:"
    echo "  cd \"$OUT\" && zip -r \"$APP_NAME.zip\" \"$APP_NAME.app\""
fi

echo ""
echo -e "${CYAN}${BOLD}Build complete.${NC}"
echo "Output folder: $OUT"
