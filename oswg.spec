# PyInstaller spec for OSWG
# Run with: pyinstaller oswg.spec

import sys
from pathlib import Path

block_cipher = None

# Determine paths
PROJECT_ROOT = Path(SPECPATH)
STATIC_PATH = PROJECT_ROOT / "src" / "oswg" / "static"

a = Analysis(
    ["src/oswg/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[
        (str(STATIC_PATH / "*"), "oswg/static/"),
    ],
    hiddenimports=[
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.loops.uvloop",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "uvicorn.lifespan.logs",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.wsproto_impl",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.main",
        "uvicorn.config",
        "aiosqlite",
        "httpx",
        "lxml",
        "lxml._elementpath",
        "lxml.etree",
        "rich",
        "typer",
        "pydantic_settings",
        "multipart",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "pytest",
        "test",
        "tests",
        "pydoc",
        "doctest",
        "setuptools",
        "distutils",
        "pip",
        "pkg_resources",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="oswg",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="oswg-bin",
)
