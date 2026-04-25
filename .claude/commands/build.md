Build the MetePDF desktop application into a standalone .exe using PyInstaller.
Work inside the `C:\Users\Ryan\any2pdf` directory for all steps.

## Step 1 — install PyInstaller
Run:
```
uv pip install pyinstaller --python .venv
```

## Step 2 — generate icon
Run:
```
.venv\Scripts\python.exe generate_icon.py
```
If it fails due to a missing font, that is OK — the icon will use a fallback font. Continue.

## Step 3 — clean previous build
If the `dist/` or `build/` folders exist, delete them:
```
rmdir /s /q dist build 2>nul
```

## Step 4 — build the .exe
Run:
```
.venv\Scripts\python.exe -m PyInstaller metepdf.spec --noconfirm
```
This may take 1-3 minutes. Show the output to the user.

## Step 5 — verify and report
After the build completes:
- Check that `dist\MetePDF.exe` exists
- Show its file size in MB
- Tell the user: **"Abra o arquivo `dist\MetePDF.exe` para executar o app — sem terminal, sem Python instalado."**
- Remind them they can pin `MetePDF.exe` to the taskbar or create a desktop shortcut (right-click → Enviar para → Área de trabalho).
