# ocr-bin-mac

Place the optional macOS OCR bundle here if you want screenshots and scanned-image OCR to work offline in the Mac installer.

These files are bundled into the Mac app by `build-mac.sh` and copied by the installer into:

- `~/.offline-ai-workstation/ocr`

## Recommended layout

```text
ocr-bin-mac/
  tesseract
  tessdata/
    eng.traineddata
```

## Minimum expected contents

- `tesseract`
- `tessdata/eng.traineddata`

## Notes

- If this folder is missing, the Mac app still builds.
- OCR features will simply remain unavailable until you add a working Mac OCR bundle.

## What can be sourced directly

Language data:

- [eng.traineddata](https://github.com/tesseract-ocr/tessdata/blob/main/eng.traineddata)

## What still needs Mac-side verification

- the `tesseract` executable itself
- any dependent libraries required by that executable
