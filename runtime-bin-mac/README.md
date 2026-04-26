# runtime-bin-mac

Place the real macOS `llama.cpp` runtime files for the workstation here.

These files are bundled into the Mac app by `build-mac.sh` and copied by the installer into:

- `~/.offline-ai-workstation/runtime`

## Minimum expected contents

- `llama-server`

## Optional supporting files

- any required `.dylib` files next to `llama-server`

## Recommended source

Use the official `ggml-org/llama.cpp` macOS release assets and copy the working runtime files into this folder.

Recommended asset types:

- macOS Apple Silicon (`arm64`) if targeting modern Macs
- macOS Intel (`x64`) if targeting Intel Macs

If you want one installer for both, you may need a universal or dual-track packaging approach rather than one raw binary drop.
