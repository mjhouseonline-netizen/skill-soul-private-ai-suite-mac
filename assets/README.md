Drop your product branding files here.

Recommended files:
- `app.ico`
  Used by the Windows app build and the Inno Setup installer.
  Best source: a multi-size ICO containing at least 16x16, 32x32, 48x48, and 256x256.

Suggested workflow:
1. Start from a square logo on a transparent background.
2. Export a high-resolution PNG.
3. Convert it to `app.ico` with multiple embedded sizes.
4. Place the final file at `installer\assets\app.ico`.

Once `app.ico` exists:
- `build-windows.bat` will use it for the app executable.
- `build-setup.bat` / `offline-ai-workstation.iss` will use it for the installer.
