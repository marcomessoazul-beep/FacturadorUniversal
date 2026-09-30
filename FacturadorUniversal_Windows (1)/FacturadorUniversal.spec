# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

project = Path(SPECPATH).resolve()
vendor = project / "vendor"
tess = vendor / "tesseract"

datas = []
binaries = []

# Bundle vendorized Tesseract if the build script found it.
if tess.exists():
    # Include the complete folder. Tesseract expects its tessdata and DLLs next to it.
    datas.append((str(tess), "vendor/tesseract"))

datas += collect_data_files("playwright")
datas += collect_data_files("sklearn")

hiddenimports = []
hiddenimports += collect_submodules("playwright")
hiddenimports += collect_submodules("sklearn")

a = Analysis(
    ["app.py"],
    pathex=[str(project)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FacturadorUniversal",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="FacturadorUniversal",
)
