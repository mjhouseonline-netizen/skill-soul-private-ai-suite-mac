# macOS Build Notes

Build the mac version on a real macOS machine.

## Requirements

- Python 3.10 or newer
- A working Tk build for Python
- `create-dmg` if you want a drag-and-drop `.dmg`

## Build command

```bash
cd /path/to/installer
chmod +x build-mac.sh
./build-mac.sh
```

Optional:

```bash
MAC_TARGET_ARCH=universal2 ./build-mac.sh
```

Valid `MAC_TARGET_ARCH` values are `arm64`, `x86_64`, and `universal2`.

## Expected optional bundle folders

The app now looks for mac-specific bundle folders first, then falls back to the generic names.
The mac build script only bundles the mac-specific folders by default so it does not accidentally ship the current Windows binaries.

- `runtime-bin-mac` or `runtime-bin-darwin`
  Put the macOS `llama-server` binary and any required `.dylib` files here.
- `image-backend-bin-mac`
  Optional local image backend files for macOS.
- `ocr-bin-mac`
  Optional macOS Tesseract bundle.
  Recommended layout:
  - `ocr-bin-mac/tesseract`
  - `ocr-bin-mac/tessdata/eng.traineddata`
- `assets/app.icns`
  Optional macOS icon.

If those folders do not exist, the build still completes, but that feature will be unavailable on the mac app until you add the bundle.

This repo now includes placeholder folders for:

- `runtime-bin-mac/`
- `image-backend-bin-mac/`
- `ocr-bin-mac/`

Fill those folders with the real macOS payloads before producing a final release build.

For direct sourcing guidance, see:

- `SOURCING-PAYLOADS.md`

If you intentionally stored mac-ready assets in the generic folder names, you can opt in with:

```bash
ALLOW_GENERIC_MAC_BUNDLES=1 ./build-mac.sh
```

## Output

- App bundle: `dist/mac/Offline-AI-Workstation.app`
- DMG: `dist/mac/Offline-AI-Workstation.dmg` if `create-dmg` is installed

## Notes

- The app now creates a mac launcher at `~/.offline-ai-workstation/Open-Offline-AI-Workspace.command`.
- Unsigned mac apps will trigger Gatekeeper. For internal testing, right-click the app and choose `Open`.
- For release builds, plan to add `codesign` and notarization later.
