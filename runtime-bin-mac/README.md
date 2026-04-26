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

Source:

- [ggml-org/llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases)

As of the latest checked release, example macOS assets include:

- `llama-b8833-bin-macos-arm64.tar.gz`
- `llama-b8833-bin-macos-arm64-kleidiai.tar.gz`
- `llama-b8833-bin-macos-x64.tar.gz`

Recommended first-release choice:

- use the plain `macos-arm64` archive for Apple Silicon
- use `macos-x64` only if you specifically want Intel Mac support

Recommended asset types:

- macOS Apple Silicon (`arm64`) if targeting modern Macs
- macOS Intel (`x64`) if targeting Intel Macs

If you want one installer for both, you may need a universal or dual-track packaging approach rather than one raw binary drop.

## Practical steps

1. download the right macOS archive from the official release page
2. extract it
3. copy `llama-server` into this folder
4. copy any required `.dylib` files into this folder
5. do not rename `llama-server`
