# Skill & Soul Private AI Suite Mac

This is the standalone macOS installer source repository for the Offline AI Workstation.

It is separate from the Windows website and release repository on purpose.

## What lives here

- `src/` - the standalone workstation app source
- `model-presets/` - bundled preset JSON files
- `assets/` - branding files and icon source image
- `build-mac.sh` - local macOS build script
- `.github/workflows/build-mac.yml` - GitHub Actions workflow for cloud mac builds
- `runtime-bin-mac/` - placeholder for the bundled Mac `llama.cpp` runtime
- `ocr-bin-mac/` - placeholder for the bundled Mac OCR payload
- `image-backend-bin-mac/` - placeholder for the bundled Mac image backend

## Build options

- Build on a real Mac with [MAC-BUILD.md](/E:/skill-soul-private-ai-suite-mac/MAC-BUILD.md)
- Build on GitHub without owning a Mac with [BUILD-ON-GITHUB.md](/E:/skill-soul-private-ai-suite-mac/BUILD-ON-GITHUB.md)

## Important gap

The repository is ready for mac builds, but a fully working release still needs mac-native runtime assets added later:

- `runtime-bin-mac/`
- `image-backend-bin-mac/`
- `ocr-bin-mac/`
- `assets/app.icns`

Without those folders, the app can still build, but bundled runtime and OCR features will be unavailable on macOS.
