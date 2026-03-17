# rthook_texture2d.py
# PyInstaller runtime hook -- runs before any user code.
# 1. Adds texture2ddecoder / etcpak .pyd directories to sys.path
# 2. Adds ALL native DLL subdirectories to os.environ["PATH"] so Windows
#    can resolve dependencies (including fmod.dll) when UnityPy loads them.
# 3. Force-imports texture2ddecoder and etcpak into sys.modules early.

import sys
import os
import ctypes

if getattr(sys, "frozen", False):
    base = sys._MEIPASS

    # ------------------------------------------------------------------
    # Step 1 -- build a list of every directory under _internal\ that
    # contains at least one .pyd or .dll file, then add them all to both
    # sys.path (for Python imports) and PATH (for Windows DLL resolution).
    # ------------------------------------------------------------------
    native_dirs = set()
    native_dirs.add(base)

    for root, dirs, files in os.walk(base):
        for fname in files:
            if fname.lower().endswith((".pyd", ".dll", ".so")):
                native_dirs.add(root)
                break  # one match is enough to include this dir

    # Add to sys.path for Python frozen importer
    for d in native_dirs:
        if d not in sys.path:
            sys.path.insert(0, d)

    # Add to PATH for Windows DLL loader (resolves fmod.dll and its deps)
    existing_path = os.environ.get("PATH", "")
    extra_path = os.pathsep.join(
        d for d in native_dirs if d not in existing_path
    )
    if extra_path:
        os.environ["PATH"] = extra_path + os.pathsep + existing_path

    # ------------------------------------------------------------------
    # Step 2 -- explicitly find and ctypes-load fmod.dll first, since
    # it is the DLL UnityPy always tries to load during asset save and
    # it lives in a deeply nested subdirectory.
    # ------------------------------------------------------------------
    for root, dirs, files in os.walk(base):
        for fname in files:
            if fname.lower() == "fmod.dll":
                fmod_path = os.path.join(root, fname)
                try:
                    ctypes.CDLL(fmod_path)
                except OSError:
                    pass  # will surface as a real error later if needed

    # ------------------------------------------------------------------
    # Step 3 -- force-load texture decoders via ctypes then import them
    # ------------------------------------------------------------------
    _targets = ("texture2ddecoder", "etcpak")
    for root, dirs, files in os.walk(base):
        for fname in files:
            if fname.endswith(".pyd") and any(t in fname for t in _targets):
                fpath = os.path.join(root, fname)
                try:
                    ctypes.CDLL(fpath)
                except OSError:
                    pass

    try:
        import texture2ddecoder  # noqa
    except ImportError:
        pass

    try:
        import etcpak  # noqa
    except ImportError:
        pass
