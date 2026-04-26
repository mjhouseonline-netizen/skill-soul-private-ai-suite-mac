# Build On GitHub Without Owning a Mac

You can build the mac version on GitHub's hosted macOS machines.

## What this gives you

- A real macOS build runner
- A downloadable `.app`
- A `.dmg` if `create-dmg` succeeds

## Limits

- The app will be unsigned unless you later add Apple signing secrets
- You still need mac-ready binaries in the installer folder for the local runtime and OCR if you want those features on macOS

## Files added for this

- `.github/workflows/build-mac.yml`
- `build-mac.sh`

## Folder layout you should upload

At minimum, the GitHub repo should contain:

- `src/`
- `model-presets/`
- `build-mac.sh`
- `.github/workflows/build-mac.yml`

Optional mac-specific folders:

- `runtime-bin-mac`
- `image-backend-bin-mac`
- `ocr-bin-mac`
- `assets/app.icns`

## Fastest path

1. Create a new private GitHub repo.
2. Upload this folder's contents into the repo root.
3. Commit and push.
4. Open the repo on GitHub.
5. Go to `Actions`.
6. Run `Build macOS Installer`.
7. Choose `arm64` for Apple Silicon or `universal2` if you want one build that targets both Apple Silicon and Intel.
8. Download the artifact when the run finishes.

## Important note about runtime bundles

Right now your Windows source tree contains Windows runtime files in the generic folders.
For a real working mac release, add mac-native assets before running the workflow:

- `runtime-bin-mac/llama-server`
- any required `.dylib` files next to it
- `ocr-bin-mac/tesseract`
- `ocr-bin-mac/tessdata/eng.traineddata`

If you skip those folders, the app should still build, but the bundled local runtime and OCR features will be unavailable on macOS until you add them.

## If you want signing later

That can also be done in GitHub Actions, but it requires:

- an Apple Developer account
- signing certificates
- notarization credentials stored as GitHub secrets
