# image-backend-bin-mac

Place the optional macOS local image backend bundle here if you want Image Studio to ship with a bundled backend inside the Mac installer.

These files are bundled into the Mac app by `build-mac.sh` and copied by the installer into:

- `~/.offline-ai-workstation/image-backend`

## Recommended layout

```text
image-backend-bin-mac/
  start-image-backend.sh
  ComfyUI-mac/
    run.sh
    main.py
    workflows/
      text-to-image.json
      premium-poster.json
    models/
      checkpoints/
        your-model.safetensors
```

## Notes

- If this folder is missing, the Mac app still builds.
- Image Studio can still open, but local backend launch/generation will not work until the bundle exists.
- The shared image-pack repo already contains a scaffold for this folder structure.
