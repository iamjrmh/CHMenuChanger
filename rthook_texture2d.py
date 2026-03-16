# rthook_texture2d.py
# PyInstaller runtime hook -- runs before any user code.
# Actively imports texture2ddecoder and etcpak so their .pyd files are
# loaded and cached in sys.modules before UnityPy tries to use them.
# Also uses ctypes to manually load the .pyd as a DLL as a fallback,
# which forces Windows to resolve its dependencies immediately and gives
# a clear error if something is still missing.

import sys
import os
import ctypes

if getattr(sys, "frozen", False):
    base = sys._MEIPASS

    # Step 1 -- ensure base and every direct subfolder are on sys.path
    if base not in sys.path:
        sys.path.insert(0, base)
    for entry in os.listdir(base):
        full = os.path.join(base, entry)
        if os.path.isdir(full) and full not in sys.path:
            sys.path.insert(0, full)

    # Step 2 -- find every .pyd belonging to texture2ddecoder or etcpak
    # and force-load it via ctypes so Windows resolves its DLL dependencies
    # right now at startup, rather than silently failing later inside UnityPy.
    _targets = ("texture2ddecoder", "etcpak")
    for root, dirs, files in os.walk(base):
        for fname in files:
            if fname.endswith(".pyd") and any(t in fname for t in _targets):
                fpath = os.path.join(root, fname)
                try:
                    ctypes.CDLL(fpath)
                except OSError:
                    pass  # missing VC++ runtime -- will surface as a real error later

    # Step 3 -- now import them so they sit in sys.modules before UnityPy loads
    try:
        import texture2ddecoder  # noqa
    except ImportError:
        pass  # runtime hook must never crash the app -- UnityPy will handle it

    try:
        import etcpak  # noqa
    except ImportError:
        pass
