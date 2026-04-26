# Mac Builder Handoff Checklist

Use this file as the shortest path for handing the Mac build work to someone else.

## Goal

Produce:

- a working Mac workstation installer from this repo
- optionally, a later Mac image-pack add-on from the shared image-pack repo

## Do these steps in order

1. Read [SOURCING-PAYLOADS.md](/E:/skill-soul-private-ai-suite-mac/SOURCING-PAYLOADS.md).

2. Fill `runtime-bin-mac/` with the real `llama.cpp` Mac runtime:
   - download the official `llama.cpp` macOS release archive
   - copy `llama-server`
   - copy any required `.dylib` files

3. Decide whether v1 includes OCR:
   - if no, leave `ocr-bin-mac/` empty
   - if yes, add a working Mac `tesseract` bundle and `tessdata/eng.traineddata`

4. Decide whether v1 includes a bundled image backend:
   - if no, leave `image-backend-bin-mac/` empty
   - if yes, assemble and test the backend using the image-pack repo docs

5. Optionally add `assets/app.icns` for a polished app icon.

6. Run the GitHub Actions workflow:
   - repo: `skill-soul-private-ai-suite-mac`
   - workflow: `Build macOS Installer`
   - recommended first target: `arm64`

7. Test the built app on a real Mac:
   - app opens
   - chat/runtime works
   - OCR works if included
   - Image Studio works if included

## Minimum viable first release

The fastest realistic v1 is:

- include `runtime-bin-mac/`
- skip OCR
- skip bundled image backend
- optionally skip custom icon

That gives you a Mac workstation installer with the local runtime, while leaving image generation as a later add-on.

## If including image generation later

Use the separate shared repo:

- `skill-soul-private-ai-suite-image-pack`

Start with:

- `mac/ASSEMBLE-MAC-IMAGE-PACK.md`
- `mac/COMFYUI-MAC-BUNDLE-CHECKLIST.md`

## If something is unclear

Read these next:

- [MAC-BUILD.md](/E:/skill-soul-private-ai-suite-mac/MAC-BUILD.md)
- [runtime-bin-mac/README.md](/E:/skill-soul-private-ai-suite-mac/runtime-bin-mac/README.md)
- [ocr-bin-mac/README.md](/E:/skill-soul-private-ai-suite-mac/ocr-bin-mac/README.md)
- [image-backend-bin-mac/README.md](/E:/skill-soul-private-ai-suite-mac/image-backend-bin-mac/README.md)
