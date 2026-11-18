# Pavouk

Clickable tournament bracket (*pavouk*) for 8 teams: click the team that won and it moves to the next round. Czech UI, PySide6 + QML.

![screenshot](screenshot.png)

- **Click a team** → it wins the match and advances. Click it again to undo.
- Changing an earlier result clears the later matches that depended on it.
- Results save automatically (survive closing the app).
- **Nový turnaj** (click twice) clears everything. **F11** = fullscreen (projector).
- Team names come from `tymy.txt` next to the app (one per line, 8 lines; created on first start). Change the names there and restart.

## Download (Windows)

Grab `Pavouk.exe` from the [latest release](../../releases/latest). No install needed. Windows SmartScreen may warn because the exe is unsigned: *More info → Run anyway*.

## Run from source

```bash
pip install PySide6-Essentials
python -m pavouk            # window
python -m pavouk --vypis    # print the bracket to the terminal
```

Tests: `pip install pytest pytest-qt && QT_QPA_PLATFORM=offscreen pytest`.

License: MIT.
