# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_all

ctk_datas = collect_data_files("customtkinter")
dnd_datas, dnd_binaries, dnd_hidden = collect_all("tkinterdnd2")

a = Analysis(
    ["gui.py"],
    pathex=["."],
    binaries=dnd_binaries,
    datas=ctk_datas + dnd_datas + [("assets/icon.png", "assets")],
    hiddenimports=[
        "converters",
        "converters.base",
        "converters.txt_converter",
        "converters.image_converter",
        "converters.docx_converter",
        "converters.pdf_converter",
        "core",
        "core.dispatcher",
        "core.exceptions",
        "utils",
        "utils.file_utils",
        "PIL._tkinter_finder",
        "reportlab.graphics.barcode.common",
        "reportlab.graphics.barcode.code128",
        "reportlab.graphics.barcode.code93",
        "reportlab.graphics.barcode.usps",
        "reportlab.graphics.barcode.usps4s",
        "reportlab.graphics.barcode.ecc200datamatrix",
    ] + dnd_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="UniversalPDF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
    version_file=None,
)
