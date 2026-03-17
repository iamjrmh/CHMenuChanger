# =============================================================================
#  CHMenuChanger.spec  --  Production PyInstaller spec
#  Auto-generated  |  Targets: Windows x64, Python 3.11, UnityPy 1.25.0
# =============================================================================

from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None


def _safe_collect(pkg):
    try:
        d, b, h = collect_all(pkg)
        return d, b, h
    except Exception:
        return [], [], []


# -- Collect all UnityPy pieces -----------------------------------------------
up_datas,     up_binaries,    up_hidden    = collect_all("UnityPy")

# -- Pillow image plugins ------------------------------------------------------
pil_datas,    pil_binaries,   pil_hidden   = collect_all("PIL")

# -- Compression backends ------------------------------------------------------
brotli_d,     brotli_b,       brotli_h     = _safe_collect("brotli")
brotlicffi_d, brotlicffi_b,  brotlicffi_h = _safe_collect("brotlicffi")
lz4_d,        lz4_b,          lz4_h        = _safe_collect("lz4")

# -- Native texture decoders via collect_all ----------------------------------
t2d_d,        t2d_b,          t2d_h        = _safe_collect("texture2ddecoder")
etcpak_d,     etcpak_b,       etcpak_h     = _safe_collect("etcpak")

# -- archspec: CPU detection library pulled in by etcpak ----------------------
# Ships JSON data files that MUST be bundled or it raises FileNotFoundError
# at runtime (archspec/json/cpu/microarchitectures.json)
archspec_d,   archspec_b,     archspec_h   = _safe_collect("archspec")

# -- fmod_toolkit + pyfmodex --------------------------------------------------
# UnityPy.export.__init__ imports AudioClipConverter at module level, which
# imports fmod_toolkit, which loads fmod.dll via pyfmodex.  The DLL lives at
# fmod_toolkit/libfmod/Windows/x64/fmod.dll -- collect_all preserves this
# exact directory structure so PyInstaller's ctypes hook finds it.
fmod_d,       fmod_b,         fmod_h       = _safe_collect("fmod_toolkit")
pyfmod_d,     pyfmod_b,       pyfmod_h     = _safe_collect("pyfmodex")

# -- Explicit top-level .pyd copies (the key fix for "Could not decode") ------
# These are resolved at spec-generation time to the exact versioned filename
# (e.g. texture2ddecoder.cp311-win_amd64.pyd) and placed at the root of
# _internal\ so Python's frozen importer finds them by name immediately.
_t2d_forced    = [('E:\\Downloads\\CHMenuChanger\\.venv\\Lib\\site-packages\\texture2ddecoder\\__init__.py', '.'), ('E:\\Downloads\\CHMenuChanger\\.venv\\Lib\\site-packages\\texture2ddecoder\\_texture2ddecoder.pyd', '.')]
_etcpak_forced = [('E:\\Downloads\\CHMenuChanger\\.venv\\Lib\\site-packages\\etcpak\\__init__.py', '.'), ('E:\\Downloads\\CHMenuChanger\\.venv\\Lib\\site-packages\\etcpak\\_etcpak_avx2.cp37-win_amd64.pyd', '.'), ('E:\\Downloads\\CHMenuChanger\\.venv\\Lib\\site-packages\\etcpak\\_etcpak_avx512.cp37-win_amd64.pyd', '.'), ('E:\\Downloads\\CHMenuChanger\\.venv\\Lib\\site-packages\\etcpak\\_etcpak_none.pyd', '.'), ('E:\\Downloads\\CHMenuChanger\\.venv\\Lib\\site-packages\\etcpak\\_etcpak_sse41.cp37-win_amd64.pyd', '.')]

# -- Merge all collected pieces ------------------------------------------------
all_datas = (
    up_datas + pil_datas +
    brotli_d + brotlicffi_d + lz4_d +
    t2d_d + etcpak_d + archspec_d +
    fmod_d + pyfmod_d
)

all_binaries = (
    up_binaries + pil_binaries +
    brotli_b + brotlicffi_b + lz4_b +
    t2d_b + etcpak_b + archspec_b +
    fmod_b + pyfmod_b +              # fmod.dll with correct nested path
    _t2d_forced +    # exact versioned .pyd at top level
    _etcpak_forced
)

all_hidden = list(set(
    up_hidden + pil_hidden +
    brotli_h + brotlicffi_h + lz4_h +
    t2d_h + etcpak_h + archspec_h +
    fmod_h + pyfmod_h +

    # UnityPy 1.25.0 full submodule tree
    collect_submodules("UnityPy") +
    collect_submodules("UnityPy.files") +
    collect_submodules("UnityPy.classes") +
    collect_submodules("UnityPy.streams") +
    collect_submodules("UnityPy.helpers") +
    collect_submodules("UnityPy.enums") +
    collect_submodules("UnityPy.tools") +
    collect_submodules("UnityPy.export") +
    collect_submodules("UnityPy.math") +
    collect_submodules("UnityPy.downloader") +
    collect_submodules("fmod_toolkit") +
    collect_submodules("pyfmodex") +

    # Pillow plugins
    collect_submodules("PIL") +

    # archspec (CPU detection, required by etcpak)
    collect_submodules("archspec") +
    collect_submodules("archspec.cpu") +

    # Compression
    [
        "brotli", "brotlicffi", "_brotli",
        "lz4", "lz4.block", "lz4.frame", "lz4.stream",
    ] +

    # Native decoders
    [
        "texture2ddecoder",
        "texture2ddecoder.texture2ddecoder",
        "etcpak",
    ] +

    # stdlib items PyInstaller sometimes misses
    [
        "ctypes", "ctypes.util", "ctypes.wintypes",
        "xml.etree.ElementTree",
        "logging",
        "logging.handlers",
        "importlib.metadata",
        "importlib.resources",
        "zlib", "_struct",
    ] +

    # tkinter
    [
        "tkinter", "tkinter.ttk",
        "tkinter.filedialog", "tkinter.messagebox",
        "tkinter.simpledialog", "_tkinter",
    ]
))

a = Analysis(
    ["clone_hero_bg_changer.py"],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["rthook_texture2d.py"],
    excludes=[
        # setuptools MUST be excluded -- it ships setuptools/logging.py which
        # shadows the stdlib logging module and breaks PIL's import.
        "setuptools",
        "setuptools.logging",
        "test", "unittest",
        "IPython", "jupyter", "notebook",
        "matplotlib", "numpy", "scipy", "pandas",
        "PyQt5", "PyQt6", "wx",
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
    name="CHMenuChanger",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='E:\\Downloads\\JURMRWEED.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CHMenuChanger",
)
