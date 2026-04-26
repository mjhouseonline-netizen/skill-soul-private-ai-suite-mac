# Sourcing Mac Payloads

This guide explains how to source the missing payloads for the Mac installer and where each one should go in this repo.

## Quick summary

You can source some payloads by direct download only.
Other payloads still need to be assembled and tested on a real Mac.

## Payload map

### `runtime-bin-mac/`

Status:
- direct download is realistic

What it is:
- the local `llama.cpp` runtime used by the workstation app

Where to get it:
- official `llama.cpp` GitHub releases:
  [ggml-org/llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases)

What to download:
- for Apple Silicon: a macOS `arm64` release archive
- for Intel Mac: a macOS `x64` release archive

As of the latest checked release, examples include:

- `llama-b8833-bin-macos-arm64.tar.gz`
- `llama-b8833-bin-macos-arm64-kleidiai.tar.gz`
- `llama-b8833-bin-macos-x64.tar.gz`

Typical asset names change over time, but look for names like:

- `llama-<version>-bin-macos-arm64.tar.gz`
- `llama-<version>-bin-macos-x64.tar.gz`

What to copy into `runtime-bin-mac/`:
- `llama-server`
- any required `.dylib` files shipped beside it

Recommended first-release choice:

- use the plain `macos-arm64` archive for Apple Silicon Macs
- skip the `kleidiai` variant unless you intentionally want that specific build

What to do next:
1. extract the release archive
2. find `llama-server`
3. copy `llama-server` into `runtime-bin-mac/`
4. copy any required `.dylib` files into `runtime-bin-mac/`
5. keep the files flat in that folder unless you intentionally change the app-side lookup
6. do not rename `llama-server`

### `ocr-bin-mac/`

Status:
- partial direct download is possible
- final usable bundle still needs Mac-side verification

What it is:
- optional offline OCR for screenshots and scanned images

What is easy to source:
- `eng.traineddata`

Where to get language data:
- official Tesseract tessdata repository:
  [tessdata/eng.traineddata](https://github.com/tesseract-ocr/tessdata/blob/main/eng.traineddata)

What is harder:
- the `tesseract` Mac executable plus any dependent libraries

Recommended approach:
1. source or build a working Mac `tesseract` binary on a Mac
2. place it in `ocr-bin-mac/tesseract`
3. place `eng.traineddata` in `ocr-bin-mac/tessdata/eng.traineddata`
4. verify the binary runs on a real Mac before shipping

### `image-backend-bin-mac/`

Status:
- not realistically “download-only” as a clean portable bundle
- should be assembled on a real Mac

What it is:
- optional local image backend for Image Studio

Recommended source path:
- official ComfyUI manual install docs:
  [ComfyUI manual install](https://docs.comfy.org/installation/manual_install)
- ComfyUI mac desktop docs for reference:
  [ComfyUI Mac desktop](https://docs.comfy.org/installation/desktop/macos)

Recommended approach:
1. on a Mac, create a working ComfyUI install
2. verify it launches with API mode on `127.0.0.1:7860`
3. copy that working install into `image-backend-bin-mac/`
4. add the model checkpoint in the supported `models/checkpoints/` folder
5. test it with the workstation app

For the detailed Mac image-pack path, see the shared image-pack repo:
- [skill-soul-private-ai-suite-image-pack](https://github.com/mjhouseonline-netizen/skill-soul-private-ai-suite-image-pack)

### `assets/app.icns`

Status:
- direct creation or download is realistic

What it is:
- optional polished Mac app icon

What to do:
1. create or convert a square source image into `.icns`
2. place it at `assets/app.icns`
3. `build-mac.sh` will pick it up automatically

## Lowest-friction release plan

If you want the fastest path to a first Mac installer release:

1. source `runtime-bin-mac/` from official `llama.cpp` release assets
2. leave `ocr-bin-mac/` empty for v1
3. leave `image-backend-bin-mac/` empty in the installer for v1
4. ship image generation later as a separate Mac image-pack add-on
5. add `assets/app.icns` only if you want a polished icon before first release

## Recommended v1 split

- installer repo:
  `skill-soul-private-ai-suite-mac`
  include `runtime-bin-mac/`
- image-pack repo:
  `skill-soul-private-ai-suite-image-pack`
  handle the optional Mac image backend there later

## Final note

The easiest payload to source right now is `runtime-bin-mac/`.
The hardest payload is `image-backend-bin-mac/`, because it needs real Mac-side assembly and testing.
