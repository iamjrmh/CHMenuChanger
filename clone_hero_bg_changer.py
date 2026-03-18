"""
CHMenuChanger  by JURMR
========================
Clone Hero Menu Background Changer

Dependencies (install once):
    pip install Pillow UnityPy

Python 3.9+

NOTE: The Clone Hero launcher resets game files after every launch.
See the welcome screen for details on how to set up your install correctly.
"""

import os
import sys
import json
import copy
import shutil
import re
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# -- Dependency handling -------------------------------------------------------
# When running as a compiled .exe (PyInstaller), all packages are bundled
# inside the executable -- no Python install required on the user's machine.
# When running as a plain .py script, offer to pip-install missing packages.

import subprocess as _subprocess

def _check_deps():
    # PyInstaller sets sys.frozen = True inside compiled exes.
    # All deps are already bundled there -- skip install logic entirely.
    if getattr(sys, "frozen", False):
        return

    missing = []
    try:
        from PIL import Image  # noqa
    except ImportError:
        missing.append("Pillow")
    try:
        import UnityPy  # noqa
    except ImportError:
        missing.append("UnityPy")

    if not missing:
        return

    exe     = sys.executable
    pkgs    = missing[:]
    pip_cmd = [exe, "-m", "pip", "install"] + pkgs

    import tkinter as _tk
    from tkinter import messagebox as _mb

    _root = _tk.Tk()
    _root.withdraw()
    answer = _mb.askyesno(
        "Install required packages",
        ("The following package(s) are missing:\n\n"
         + "\n".join("  - " + m for m in missing)
         + "\n\nPython: " + exe
         + "\n\nClick YES to install now. Click NO to exit."),
        icon="warning"
    )
    _root.destroy()
    if not answer:
        sys.exit(0)

    _pr = _tk.Tk()
    _pr.title("Installing...")
    _pr.configure(bg="#0c0e13")
    _pr.resizable(False, False)
    _pr.geometry("500x120")
    _tk.Label(_pr, text="Installing: " + " ".join(pkgs),
              font=("Segoe UI", 11), bg="#0c0e13", fg="#e9ecf8", pady=20).pack()
    _tk.Label(_pr, text="Running pip, please wait...",
              font=("Consolas", 9), bg="#0c0e13", fg="#9aa3bf").pack()
    _pr.update()

    try:
        _cflags = 0x08000000 if sys.platform == "win32" else 0
        result  = _subprocess.run(pip_cmd, capture_output=True,
                                  text=True, timeout=180, creationflags=_cflags)
    except Exception as ex:
        _pr.destroy()
        _r = _tk.Tk(); _r.withdraw()
        _mb.showerror("Install error", str(ex)); _r.destroy()
        sys.exit(1)

    _pr.destroy()

    if result.returncode != 0:
        _r = _tk.Tk(); _r.withdraw()
        _mb.showerror("pip failed",
                      "pip exited with code {}:\n\n{}".format(
                          result.returncode,
                          (result.stderr or result.stdout)[:600]))
        _r.destroy()
        sys.exit(1)

    still = []
    try:
        from PIL import Image  # noqa
    except ImportError:
        still.append("Pillow")
    try:
        import UnityPy  # noqa
    except ImportError:
        still.append("UnityPy")

    if still:
        fix_cmd = " ".join(
            ('"' + p + '"' if " " in p else p) for p in pip_cmd
        )
        _r = _tk.Tk(); _r.withdraw()
        try:
            _r.clipboard_clear(); _r.clipboard_append(fix_cmd); _r.update()
        except Exception:
            pass
        _mb.showerror("Still missing",
                      ("Packages installed but still not importable.\n\n"
                       "This usually means there are multiple Python installs.\n\n"
                       "The fix command has been copied to your clipboard.\n"
                       "Paste it in a terminal and restart:\n\n" + fix_cmd))
        _r.destroy()
        sys.exit(1)

    _r = _tk.Tk(); _r.withdraw()
    _mb.showinfo("Success", "Packages installed!\nThe app will now start.")
    _r.destroy()

_check_deps()

from PIL import Image, ImageTk
import UnityPy

# -- Persistent storage --------------------------------------------------------

# When running as a compiled exe, store config next to the exe.
# When running as a script, store it next to the script.
def _app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent

CONFIG_FILE   = _app_dir() / "ch_bg_config.json"
PROFILES_FILE = _app_dir() / "ch_bg_profiles.json"
SCAN_LOG_FILE = _app_dir() / "ch_bg_scan.log"

# CH Launcher install registry – used for silent patching
_INSTALLS_FILE = Path(os.environ.get("APPDATA", "")) / \
    "net.clonehero" / "ch_launcher" / "game_installs.json"


def _silent_patch_as_manual(install_folder: str) -> str:
    """
    Silently mark the matching Clone Hero install as isFromLauncher=false
    so the Launcher treats it as a manually-managed install.

    Returns a short status string (logged but never shown in a dialog).
    No exceptions are raised – any failure is caught and returned as a message.
    """
    installs_path = _INSTALLS_FILE
    if not installs_path.is_file():
        return "game_installs.json not found – skipping launcher patch"

    backup_path = Path(str(installs_path) + ".bak")
    try:
        shutil.copy2(str(installs_path), str(backup_path))
    except Exception as e:
        return f"Could not create backup of game_installs.json: {e}"

    try:
        data = json.loads(installs_path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Could not read game_installs.json: {e}"

    # Normalise both paths for comparison (forward-slash, lower-case)
    def _norm_path(p):
        return str(p).replace("\\", "/").rstrip("/").lower()

    target = _norm_path(install_folder)
    patched = 0
    for install in data.get("installs", []):
        if _norm_path(install.get("directoryPath", "")) == target:
            install["isFromLauncher"]  = False
            install["manifestVersion"] = None
            install["manifestDate"]    = None
            patched += 1

    if patched == 0:
        return (
            f"No matching install found in game_installs.json for:\n  {install_folder}\n"
            "You may need to add it to the Launcher manually and re-confirm."
        )

    try:
        installs_path.write_text(
            json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        return f"Could not save patched game_installs.json: {e}"

    return f"Launcher patch applied ({patched} install(s) set to Manual)"


# Process names the CH Launcher is known to run under
_LAUNCHER_PROCS = ("CloneHeroLauncher.exe", "ch_launcher.exe", "clone-hero-launcher.exe")

def _kill_launcher() -> bool:
    """
    Force-kill the Clone Hero Launcher if it is running.
    Returns True if at least one process was terminated, False otherwise.
    Silently swallows all errors.
    """
    killed = False
    if sys.platform == "win32":
        for proc in _LAUNCHER_PROCS:
            try:
                flags = 0x08000000  # CREATE_NO_WINDOW
                result = _subprocess.run(
                    ["taskkill", "/F", "/IM", proc],
                    capture_output=True, creationflags=flags)
                if result.returncode == 0:
                    killed = True
            except Exception:
                pass
    else:
        for proc in _LAUNCHER_PROCS:
            try:
                result = _subprocess.run(
                    ["pkill", "-9", "-f", proc], capture_output=True)
                if result.returncode == 0:
                    killed = True
            except Exception:
                pass
    return killed


def _launcher_is_running() -> bool:
    """Return True if any known launcher process is currently running."""
    if sys.platform == "win32":
        try:
            flags = 0x08000000
            out = _subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq CloneHeroLauncher.exe",
                 "/NH", "/FO", "CSV"],
                capture_output=True, text=True, creationflags=flags).stdout
            if "CloneHeroLauncher.exe" in out:
                return True
            # Also check the alternate name
            out2 = _subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq ch_launcher.exe",
                 "/NH", "/FO", "CSV"],
                capture_output=True, text=True, creationflags=flags).stdout
            return "ch_launcher.exe" in out2
        except Exception:
            return False
    else:
        for proc in _LAUNCHER_PROCS:
            try:
                r = _subprocess.run(["pgrep", "-f", proc], capture_output=True)
                if r.returncode == 0:
                    return True
            except Exception:
                pass
        return False


def _get_default_data():
    """Return the best known data path: saved config value, or the hardcoded fallback."""
    cfg = _load_json(CONFIG_FILE, {})
    return cfg.get("default_data_path", DEFAULT_DATA)

def _log(msg: str):
    """Append a timestamped line to the scan log and print it."""
    import datetime
    line = "[{}] {}".format(datetime.datetime.now().strftime("%H:%M:%S"), msg)
    print(line)
    try:
        with open(SCAN_LOG_FILE, "a", encoding="utf-8") as _lf:
            _lf.write(line + "\n")
    except Exception:
        pass

def _load_json(path: Path, default):
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def _save_json(path: Path, data):
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[save_json] {path}: {e}")


# -- Background catalogue ------------------------------------------------------

# Name of the locked read-only "factory default" profile
DEFAULT_PROFILE_NAME = "Default (Original)"

BACKGROUNDS = [
    "Black", "Spray", "Pastel Burst", "Groovy", "Grains",
    "Blue Rays", "Alien", "Autumn", "Light", "Dark",
    "Classic", "Surfer", "SurferAlt", "Rainbow", "Animated",
    "Logo_Transparent",       # exact asset name; lives in globalgamemanagers.assets
]

# Exact asset name -> exact source filename mapping (overrides fuzzy matching)
EXACT_ASSET_FILE = {
    "Logo_Transparent": "globalgamemanagers.assets",
}

DEFAULT_DATA = str(
    Path.home() / "Documents" / "Clone Hero" / "Clone Hero_Data"
)


def required_size(name: str):
    return (2030, 1328) if name == "Logo_Transparent" else (1920, 1080)

def exact_match_required(name: str) -> bool:
    return name == "Logo_Transparent"

def _norm(s: str) -> str:
    return re.sub(r"[\s_\-]", "", s).lower()


# -- Colour / font constants ---------------------------------------------------

C = dict(
    bg="#0c0e13", panel="#13161f", card="#181c28", card2="#1c2030",
    border="#252b3d", border2="#2e3650",
    accent="#6c3bff", accent_dim="#3d2299", accent2="#ff3b8a", accent3="#00d4aa",
    text="#e9ecf8", text_dim="#636b82", text_mid="#9aa3bf",
    success="#22c55e", warn="#f59e0b", error="#ef4444",
    selected="#341a7a", hover="#1e2235",
)

FT  = ("Segoe UI", 10)
FTB = ("Segoe UI", 10, "bold")
FTS = ("Segoe UI", 8)
FTH = ("Segoe UI", 13, "bold")
FTT = ("Segoe UI", 20, "bold")
FTM = ("Consolas", 9)


# -- UnityPy asset manager -----------------------------------------------------

class AssetManager:
    """
    Loads every .assets file (and globalgamemanagers itself) found inside
    Clone Hero_Data, indexes all Texture2D objects by name, and writes back
    only the specific file(s) that were actually modified.

    The user selects the Clone Hero_Data folder directly.
    """

    def __init__(self, data_dir):
        """
        data_dir: path to  .../Clone Hero/Clone Hero_Data

        Loading strategy:
          - Load each file by FULL PATH so UnityPy can resolve sidecar resource
            files (.resS, .resource) when decoding texture pixel data.
          - At save time, call env.file.save() to get the bytes for JUST that
            one SerializedFile, then write them to disk ourselves.  We never
            call env.save() which would write all loaded files together.
        """
        self.data_dir = str(data_dir)
        self._data    = {}   # asset_name -> Texture2D data object (read once, mutate in place)
        self._env_map = {}   # asset_name -> (env, abs_file_path_str)
        self._envs    = {}   # abs_file_path_str -> env
        self._dirty   = set()

        # Clear log for this scan session
        try:
            import datetime
            with open(SCAN_LOG_FILE, "w", encoding="utf-8") as _lf:
                _lf.write("CHMenuChanger scan log -- {}\n".format(
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                _lf.write("data_dir: {}\n\n".format(data_dir))
        except Exception:
            pass

        self._scan()

    def _scan(self):
        data_dir = Path(self.data_dir)

        candidates = []
        for f in data_dir.iterdir():
            if not f.is_file():
                continue
            lo = f.name.lower()
            if f.suffix.lower() == ".assets":
                candidates.append(f)
            elif lo == "globalgamemanagers":
                candidates.append(f)

        def sort_key(p):
            n = p.name.lower()
            if n == "sharedassets1.assets":       return 0
            if n == "globalgamemanagers.assets":  return 1
            if n == "globalgamemanagers":         return 2
            if "sharedassets" in n:               return 3
            if "resources" in n:                  return 4
            return 5

        candidates.sort(key=sort_key)
        for fpath in candidates:
            self._load_file(fpath)

    def _load_file(self, fpath):
        """Load one file by path so sidecar resource files can be resolved."""
        key = str(fpath)
        if key in self._envs:
            return
        try:
            env = UnityPy.load(key)
            self._envs[key] = env
            count = 0
            for obj in env.objects:
                if obj.type.name == "Texture2D":
                    try:
                        d = obj.read()
                        n = getattr(d, "m_Name", None) or getattr(d, "name", None)
                        if n and n not in self._data:
                            self._data[n]    = d
                            self._env_map[n] = (env, key)
                            count += 1
                    except Exception as ex:
                        _log("[_load_file] read error in {}: {}".format(
                            Path(fpath).name, ex))
            if count:
                _log("[scan] {} -> {} texture(s)".format(Path(fpath).name, count))
        except Exception as e:
            _log("[scan] skipped {}: {}".format(Path(fpath).name, e))

    # -- public API ------------------------------------------------------------

    def texture_names(self):
        return list(self._data.keys())

    def source_file(self, asset_name):
        entry = self._env_map.get(asset_name)
        return entry[1] if entry else None

    def find_for_bg(self, bg):
        required_file = EXACT_ASSET_FILE.get(bg)
        if required_file:
            req_lo = required_file.lower()
            for name, (env, fpath) in self._env_map.items():
                if Path(fpath).name.lower() != req_lo:
                    continue
                if _norm(name) == _norm(bg) or _norm(bg) in _norm(name):
                    return name
            return None

        nb    = _norm(bg)
        names = list(self._data.keys())
        for n in names:
            if _norm(n) == nb: return n
        for n in names:
            if nb in _norm(n): return n
        for n in names:
            nn = _norm(n)
            if len(nn) >= 3 and nn in nb: return n
        return None

    def export_image(self, asset_name):
        """
        Decode a Texture2D to a PIL Image, trying multiple approaches.
        Returns (PIL.Image, None) on success, (None, error_str) on failure.
        """
        d = self._data.get(asset_name)
        if d is None:
            return None, "Asset \'{}\' not in cache".format(asset_name)

        errors = []

        # ------------------------------------------------------------------
        # Approach 1: standard UnityPy .image property
        # ------------------------------------------------------------------
        try:
            img = d.image
            if img is not None:
                # .image handles Unity's bottom-up storage internally -- no flip needed
                return img.convert("RGBA"), None
            errors.append("Approach 1 (.image): returned None")
        except Exception as e:
            errors.append("Approach 1 (.image): {}".format(e))

        # ------------------------------------------------------------------
        # Approach 2: read pixel data ourselves (handles .resS streaming
        # files) then call texture2ddecoder directly, bypassing UnityPy's
        # internal dynlib loader that tries to pull in FMOD and other
        # unrelated Unity native plugins.
        # ------------------------------------------------------------------
        try:
            import texture2ddecoder as _t2d
            from UnityPy.enums import TextureFormat as TF

            fmt = d.m_TextureFormat
            w   = d.m_Width
            h   = d.m_Height

            # -- Read pixel bytes ----------------------------------------------
            # Textures are stored one of two ways:
            #   a) Inline in m_ImageData  (small / uncompressed textures)
            #   b) In a sidecar .resS streaming file referenced by m_StreamData
            #      This is the common case for large PC textures and the reason
            #      m_ImageData is empty (0 bytes) causing silent decode failure.
            data = bytes(d.image_data) if d.image_data else b""

            if not data:
                # Try reading from the .resS sidecar file
                sd = getattr(d, "m_StreamData", None)
                if sd is not None:
                    res_path = getattr(sd, "path", None)
                    offset   = getattr(sd, "offset", 0)
                    size     = getattr(sd, "size",   0)
                    if res_path and size > 0:
                        # sd.path is relative to the .assets file's folder
                        entry     = self._env_map.get(asset_name)
                        asset_dir = str(Path(entry[1]).parent) if entry else self.data_dir
                        # UnityPy may embed archive:// or cab:// prefixes -- strip them
                        clean_path = res_path.split("/")[-1] if "/" in res_path else res_path
                        full_res   = os.path.join(asset_dir, clean_path)
                        if os.path.isfile(full_res):
                            with open(full_res, "rb") as rf:
                                rf.seek(offset)
                                data = rf.read(size)
                        else:
                            errors.append(
                                "Approach 2: .resS file not found: {}".format(full_res))

            if not data:
                errors.append("Approach 2: pixel data is empty after resS attempt")
            else:
                _BC_MAP = {
                    TF.DXT1:             (_t2d.decode_bc1,    "BGRA"),
                    TF.DXT1Crunched:     (_t2d.decode_bc1,    "BGRA"),
                    TF.DXT5:             (_t2d.decode_bc3,    "BGRA"),
                    TF.DXT5Crunched:     (_t2d.decode_bc3,    "BGRA"),
                    TF.BC4:              (_t2d.decode_bc4,    "BGRA"),
                    TF.BC5:              (_t2d.decode_bc5,    "BGRA"),
                    TF.BC6H:             (_t2d.decode_bc6,    "BGRA"),
                    TF.BC7:              (_t2d.decode_bc7,    "BGRA"),
                    TF.ETC_RGB4:         (_t2d.decode_etc1,   "BGRA"),
                    TF.ETC_RGB4Crunched: (_t2d.decode_etc1,   "BGRA"),
                    TF.ETC2_RGB:         (_t2d.decode_etc2,   "BGRA"),
                    TF.ETC2_RGBA8:       (_t2d.decode_etc2a8, "BGRA"),
                    TF.ETC2_RGBA1:       (_t2d.decode_etc2a1, "BGRA"),
                }

                _RAW_MAP = {
                    TF.Alpha8:   ("L",    "raw", "L"),
                    TF.ARGB4444: ("RGBA", "raw", "RGBA;4B"),
                    TF.RGB24:    ("RGBA", "raw", "RGB"),
                    TF.RGBA32:   ("RGBA", "raw", "RGBA"),
                    TF.ARGB32:   ("RGBA", "raw", "ARGB"),
                    TF.BGRA32:   ("RGBA", "raw", "BGRA"),
                    TF.R8:       ("L",    "raw", "L"),
                    TF.RG16:     ("RGB",  "raw", "RG"),
                    TF.RGB565:   ("RGBA", "raw", "BGR;16"),
                    TF.RGBA4444: ("RGBA", "raw", "RGBA;4B"),
                }

                if fmt in _BC_MAP:
                    fn, mode = _BC_MAP[fmt]
                    raw = fn(data, w, h)
                    img = Image.frombytes("RGBA", (w, h), raw, "raw", mode)
                    return img.transpose(Image.FLIP_TOP_BOTTOM), None
                elif fmt in _RAW_MAP:
                    out_mode, decoder, raw_mode = _RAW_MAP[fmt]
                    img = Image.frombytes(out_mode, (w, h), data, decoder, raw_mode)
                    return img.convert("RGBA").transpose(Image.FLIP_TOP_BOTTOM), None
                else:
                    errors.append(
                        "Approach 2: unhandled format {} -- add it to BC_MAP or RAW_MAP".format(fmt))
        except Exception as e:
            import traceback
            full = traceback.format_exc()
            _log("[export_image] Approach 2 full traceback:\n" + full)
            errors.append("Approach 2 (direct t2d + resS): {}".format(e))

        # ------------------------------------------------------------------
        # All approaches failed -- return combined error for UI display
        # ------------------------------------------------------------------
        combined = " | ".join(errors)
        print("[export_image] {} FAILED: {}".format(asset_name, combined))
        return None, combined

    def import_image(self, asset_name, pil):
        d = self._data.get(asset_name)
        if d is None:
            return False
        rgba = pil.convert("RGBA")
        try:
            if hasattr(d, "set_image"):
                d.set_image(rgba); d.save()
                self._dirty.add(asset_name)
                _log("[WRITE OK] set_image: {}".format(asset_name))
                return True
        except Exception as e:
            _log("[WRITE FAIL] set_image '{}': {}".format(asset_name, e))
        try:
            d.image = rgba; d.save()
            self._dirty.add(asset_name)
            _log("[WRITE OK] image= setter: {}".format(asset_name))
            return True
        except Exception as e:
            _log("[WRITE FAIL] image= setter '{}': {}".format(asset_name, e))
            return False

    # -- Backup helpers --------------------------------------------------------

    BACKUP_DIR_NAME = "_CH_BG_Backups"

    def backup_dir(self):
        return os.path.join(self.data_dir, self.BACKUP_DIR_NAME)

    def needs_backup(self):
        bd = self.backup_dir()
        return [fp for fp in self._envs
                if not os.path.isfile(os.path.join(bd, Path(fp).name))]

    def has_full_backup(self):
        return len(self.needs_backup()) == 0

    def create_backups(self):
        bd = self.backup_dir()
        os.makedirs(bd, exist_ok=True)
        created, errors = [], []
        for fpath in self.needs_backup():
            dest = os.path.join(bd, Path(fpath).name)
            try:
                shutil.copy2(fpath, dest)
                created.append(dest)
            except Exception as e:
                errors.append("{}: {}".format(Path(fpath).name, e))
        return created, errors

    # -- In-place save ---------------------------------------------------------

    def save_modified(self):
        """
        Save ONLY the specific .assets file each modified texture came from.

        We call env.file.save() to get the bytes for just that one
        SerializedFile, then write them to disk ourselves.  env.file is
        the SerializedFile when loaded by path.  We never call env.save()
        which would bundle all loaded files together.
        """
        dirty_files = {}
        for name in self._dirty:
            entry = self._env_map.get(name)
            if entry:
                env, fpath = entry
                dirty_files[fpath] = env

        if not dirty_files:
            return [], ["No textures were imported - nothing to save."]

        saved, errors = [], []
        for fpath, env in dirty_files.items():
            fname = Path(fpath).name
            try:
                data = env.file.save()
                with open(fpath, "wb") as f:
                    f.write(data)
                saved.append(fpath)
            except Exception as e:
                errors.append("{}: {}".format(fname, e))

        if saved:
            self._reload_saved(saved)

        return saved, errors

    def _reload_saved(self, saved_paths):
        """Reload the just-written files by path to keep data objects fresh."""
        for fpath in saved_paths:
            try:
                env = UnityPy.load(fpath)
                self._envs[fpath] = env
                for obj in env.objects:
                    if obj.type.name == "Texture2D":
                        try:
                            d = obj.read()
                            n = getattr(d, "m_Name", None) or getattr(d, "name", None)
                            if n and n in self._data:
                                self._data[n]    = d
                                self._env_map[n] = (env, fpath)
                        except Exception:
                            pass
            except Exception as e:
                _log("[reload] {}: {}".format(Path(fpath).name, e))
        self._dirty.clear()


# -- Profile helpers -----------------------------------------------------------

def _blank_profile(name):
    return {"name": name, "data_path": _get_default_data(), "replacements": {}}

def _load_profiles():
    d = _load_json(PROFILES_FILE, {})
    return d if isinstance(d, dict) else {}

def _save_profiles(p):
    _save_json(PROFILES_FILE, p)


# -- Tooltip helper ------------------------------------------------------------

class HoverTooltip:
    """
    Attach a rich tooltip popup to any widget.
    Appears after a short delay on mouse-enter; disappears on leave.

    Usage:
        HoverTooltip(widget, "Some message text")
    """
    _PAD   = 14
    _DELAY = 400   # ms before showing

    def __init__(self, widget: tk.Widget, text: str,
                 title: str = "", width: int = 400):
        self._widget = widget
        self._text   = text
        self._title  = title
        self._width  = width
        self._win    = None
        self._job    = None
        widget.bind("<Enter>",    self._on_enter,  add="+")
        widget.bind("<Leave>",    self._on_leave,  add="+")
        widget.bind("<Button-1>", self._on_leave,  add="+")
        widget.bind("<Destroy>",  self._on_destroy, add="+")

    def _on_enter(self, _=None):
        self._cancel()
        self._job = self._widget.after(self._DELAY, self._show)

    def _on_leave(self, _=None):
        self._cancel()
        self._hide()

    def _on_destroy(self, _=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._job:
            try: self._widget.after_cancel(self._job)
            except Exception: pass
            self._job = None

    def _show(self):
        if self._win:
            return
        try:
            x = self._widget.winfo_rootx() + 24
            y = self._widget.winfo_rooty() + self._widget.winfo_height() + 6
        except Exception:
            return

        self._win = tk.Toplevel(self._widget)
        self._win.wm_overrideredirect(True)
        self._win.configure(bg=C["border"])
        self._win.attributes("-topmost", True)

        inner = tk.Frame(self._win, bg=C["card"], padx=self._PAD, pady=self._PAD)
        inner.pack(padx=1, pady=1)

        if self._title:
            tk.Label(inner, text=self._title,
                     font=("Segoe UI", 10, "bold"),
                     fg=C["warn"], bg=C["card"],
                     justify="left").pack(anchor="w", pady=(0, 6))

        tk.Label(inner, text=self._text,
                 font=("Segoe UI", 9),
                 fg=C["text_mid"], bg=C["card"],
                 justify="left", wraplength=self._width).pack(anchor="w")

        self._win.update_idletasks()
        sw = self._win.winfo_screenwidth()
        tw = self._win.winfo_reqwidth()
        if x + tw > sw - 10:
            x = sw - tw - 10
        self._win.geometry("+{}+{}".format(x, y))
        self._win.bind("<Leave>", self._on_leave)

    def _hide(self):
        if self._win:
            try: self._win.destroy()
            except Exception: pass
            self._win = None


# -- Setup dialog (first launch) -----------------------------------------------

class SetupDialog:
    """
    First-launch dialog. Asks the user to locate their Clone Hero install
    folder, then derives the _Data path automatically and saves it to config.

    After the dialog closes, call .result to get the chosen data path (str),
    or None if the user skipped.
    """

    def __init__(self, root: tk.Tk):
        self.result = None

        self.win = tk.Toplevel(root)
        self.win.title("Welcome to CHMenuChanger")
        self.win.configure(bg=C["bg"])
        self.win.resizable(False, False)
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._skip)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self.win, bg=C["panel"]); hdr.pack(fill="x")
        hi  = tk.Frame(hdr, bg=C["panel"], padx=28, pady=18); hi.pack(fill="x")
        tk.Label(hi, text="CHMenuChanger", font=("Segoe UI", 22, "bold"),
                 bg=C["panel"], fg=C["text"]).pack(side="left")
        tk.Label(hi, text="  by JURMR", font=("Segoe UI", 13),
                 bg=C["panel"], fg=C["accent"]).pack(side="left", pady=(8, 0))

        # Patch status badge – top-right of header, updated after Confirm
        self._patch_badge = tk.Label(
            hi, text="", font=("Segoe UI", 9, "bold"),
            bg=C["panel"], fg=C["text_dim"], padx=10, pady=4,
            relief="flat")
        self._patch_badge.pack(side="right", padx=(0, 4))
        self._update_patch_badge(None)  # show initial "not patched" state

        # ── Body ──────────────────────────────────────────────────────────────
        body = tk.Frame(self.win, bg=C["bg"], padx=28, pady=22)
        body.pack(fill="both")

        tk.Label(body,
                 text="Select your Clone Hero installation folder to get started.",
                 font=("Segoe UI", 11), fg=C["text"], bg=C["bg"],
                 justify="left").pack(anchor="w", pady=(0, 18))

        # Path picker card
        pick_card = tk.Frame(body, bg=C["card"],
                             highlightbackground=C["border"], highlightthickness=1,
                             padx=18, pady=16)
        pick_card.pack(fill="x", pady=(0, 10))

        tk.Label(pick_card, text="CLONE HERO INSTALL FOLDER",
                 font=("Segoe UI", 8, "bold"), fg=C["text_dim"],
                 bg=C["card"]).pack(anchor="w", pady=(0, 8))

        row = tk.Frame(pick_card, bg=C["card"]); row.pack(fill="x")
        self._path_var = tk.StringVar()
        ttk.Entry(row, textvariable=self._path_var,
                  font=FTM, style="DE.TEntry").pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Browse…", command=self._browse,
                  bg=C["accent_dim"], fg=C["text"], relief="flat",
                  font=FT, padx=10, pady=4, cursor="hand2").pack(side="left", padx=(8, 0))

        self._derived_lbl = tk.Label(pick_card, text="",
                                      font=FTM, fg=C["text_dim"],
                                      bg=C["card"], anchor="w")
        self._derived_lbl.pack(fill="x", pady=(10, 0))
        self._path_var.trace_add("write", self._on_path_change)

        # Pre-fill with the default Documents location if it exists
        default = str(Path.home() / "Documents" / "Clone Hero")
        if os.path.isdir(default):
            self._path_var.set(default)

        # Info blurb
        info_card = tk.Frame(body, bg=C["card2"],
                             highlightbackground=C["border"], highlightthickness=1,
                             padx=18, pady=14)
        info_card.pack(fill="x", pady=(4, 0))
        tk.Label(info_card,
                 text="This is the folder that contains \"Clone Hero.exe\".\n"
                      "CHMenuChanger will look for game assets inside the\n"
                      "\"Clone Hero_Data\" subfolder found within it.",
                 font=FT, fg=C["text_mid"], bg=C["card2"],
                 justify="left").pack(anchor="w")

        # ── Footer ────────────────────────────────────────────────────────────
        foot = tk.Frame(self.win, bg=C["panel"], padx=24, pady=14)
        foot.pack(fill="x")
        tk.Label(foot, text="Made by JURMR", font=FTS,
                 bg=C["panel"], fg=C["text_dim"]).pack(side="left")
        tk.Button(foot, text="Skip",
                  command=self._skip,
                  bg=C["border"], fg=C["text_dim"], relief="flat",
                  font=FT, padx=14, pady=6, cursor="hand2").pack(side="right", padx=(8, 0))
        self._confirm_btn = tk.Button(foot, text="Confirm  →",
                                       command=self._confirm,
                                       bg=C["accent"], fg="white", relief="flat",
                                       font=FTB, padx=18, pady=6, cursor="hand2")
        self._confirm_btn.pack(side="right")

        # Centre on root
        self.win.update_idletasks()
        rw = root.winfo_width()  or 900
        rh = root.winfo_height() or 700
        rx = root.winfo_rootx()
        ry = root.winfo_rooty()
        dw = self.win.winfo_reqwidth()
        dh = self.win.winfo_reqheight()
        self.win.geometry("+{}+{}".format(rx + (rw - dw)//2, ry + (rh - dh)//2))

    def _update_patch_badge(self, success: bool | None):
        """
        Update the top-right patch status badge.
          None  → not yet attempted  (neutral)
          True  → patch succeeded    (green ✓)
          False → patch failed       (red ✗)
        """
        if success is None:
            self._patch_badge.config(
                text="◦  Not Patched",
                fg=C["text_dim"],
                bg=C["panel"])
        elif success:
            self._patch_badge.config(
                text="✓  Patched",
                fg=C["success"],
                bg=C["panel"])
        else:
            self._patch_badge.config(
                text="✗  Not Patched",
                fg=C["error"],
                bg=C["panel"])

    def _browse(self):
        p = filedialog.askdirectory(
            title="Select your Clone Hero install folder",
            initialdir=self._path_var.get() or str(Path.home()))
        if p:
            self._path_var.set(p)

    def _on_path_change(self, *_):
        p = self._path_var.get().strip()
        data_path = os.path.join(p, "Clone Hero_Data") if p else ""
        if p and os.path.isdir(data_path):
            self._derived_lbl.config(
                text="  Data folder found:  {}".format(data_path),
                fg=C["success"])
            self._confirm_btn.config(state="normal", bg=C["accent"])
        elif p:
            self._derived_lbl.config(
                text="  Derived path:  {}  (not found yet)".format(data_path),
                fg=C["warn"])
            self._confirm_btn.config(state="normal", bg=C["accent"])
        else:
            self._derived_lbl.config(text="", fg=C["text_dim"])

    def _confirm(self):
        p = self._path_var.get().strip()
        if not p:
            messagebox.showerror("No folder selected",
                                 "Please choose your Clone Hero install folder.",
                                 parent=self.win)
            return
        data_path = os.path.join(p, "Clone Hero_Data")
        if not os.path.isdir(data_path):
            if not messagebox.askyesno(
                    "Folder not found",
                    "\"Clone Hero_Data\" was not found inside:\n{}\n\n"
                    "This might not be the right folder.  Continue anyway?".format(p),
                    parent=self.win):
                return

        # ── Force-close the Launcher if it's running ──────────────────────────
        if _launcher_is_running():
            killed = _kill_launcher()
            if killed:
                _log("[launcher-patch] Launcher was running – force-closed before patching")
                # Brief pause so the process fully exits before we write the JSON
                self.win.after(600, lambda: self._do_patch(p, data_path))
                return
            else:
                _log("[launcher-patch] Launcher detected but could not be killed – proceeding anyway")

        self._do_patch(p, data_path)

    def _do_patch(self, p: str, data_path: str):
        """Run the actual patch and update the badge, then close the dialog."""
        self.result = data_path

        patch_msg = _silent_patch_as_manual(p)
        _log("[launcher-patch] " + patch_msg)

        success = patch_msg.startswith("Launcher patch applied")
        self._update_patch_badge(success)

        # Leave the badge visible for a moment so the user can see it
        self.win.after(900, self.win.destroy)

    def _skip(self):
        self.result = None
        self.win.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CHMenuChanger  by JURMR")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.minsize(1160, 740)

        self._cfg      = _load_json(CONFIG_FILE, {})
        self._profiles = _load_profiles()

        # runtime state
        self._am = None  # type: AssetManager
        self._asset_cache = {}  # bg → asset_name (str or None)
        self._orig_pil = {}
        self._new_pil = {}
        self._orig_tk = {}
        self._new_tk = {}
        self._active_name = ""
        self._active_prof = {}

        self._status_v = tk.StringVar(value="Ready.")

        # first-launch check
        self.withdraw()
        self.update_idletasks()

        self._apply_styles()
        self._build_ui()
        self._load_initial_profile()
        self.deiconify()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- Boot helpers ----------------------------------------------------------

    def _load_initial_profile(self):
        # Ensure the locked Default profile always exists and stays clean
        if DEFAULT_PROFILE_NAME not in self._profiles:
            self._profiles[DEFAULT_PROFILE_NAME] = _blank_profile(DEFAULT_PROFILE_NAME)
        self._profiles[DEFAULT_PROFILE_NAME]["locked"] = True
        self._profiles[DEFAULT_PROFILE_NAME]["replacements"] = {}
        _save_profiles(self._profiles)

        last = self._cfg.get("last_profile", "")
        if last and last in self._profiles:
            self._switch_profile(last)
        elif self._profiles:
            self._switch_profile(next(iter(self._profiles)))

        # Show setup dialog on first launch to capture the CH install directory
        if not self._cfg.get("setup_done", False):
            dlg = SetupDialog(self)
            self.wait_window(dlg.win)
            if dlg.result:
                self._data_v.set(dlg.result)
                if not self._is_default_profile():
                    self._active_prof["data_path"] = dlg.result
                    _save_profiles(self._profiles)
                self._cfg["default_data_path"] = dlg.result
            self._cfg["setup_done"] = True
            _save_json(CONFIG_FILE, self._cfg)

    # -- Styles ----------------------------------------------------------------

    def _apply_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Treeview",
                    background=C["panel"], fieldbackground=C["panel"],
                    foreground=C["text"], bordercolor=C["border"],
                    rowheight=32, font=FT)
        s.map("Treeview",
              background=[("selected", C["selected"])],
              foreground=[("selected", C["text"])])
        s.configure("Treeview.Heading",
                    background=C["border"], foreground=C["text_mid"], font=FTS)
        s.configure("DE.TEntry",
                    fieldbackground=C["card2"], foreground=C["text"],
                    insertcolor=C["text"], bordercolor=C["border"])
        s.configure("Vertical.TScrollbar",
                    background=C["border"], troughcolor=C["panel"],
                    arrowcolor=C["text_dim"])
        s.configure("TCombobox",
                    fieldbackground=C["card2"], background=C["card2"],
                    foreground=C["text"], selectbackground=C["selected"],
                    selectforeground=C["text"])
        s.map("TCombobox",
              fieldbackground=[("readonly", C["card2"])],
              foreground=[("readonly", C["text"])])

    # -- UI construction -------------------------------------------------------

    def _build_ui(self):
        self._build_topbar()
        self._build_profile_bar()
        self._build_ggm_bar()
        self._build_main_area()
        self._build_statusbar()

    # -- Top bar ---------------------------------------------------------------

    def _build_topbar(self):
        f = tk.Frame(self, bg=C["panel"])
        f.pack(fill="x")
        inner = tk.Frame(f, bg=C["panel"], padx=20, pady=12)
        inner.pack(fill="x")
        tk.Label(inner, text="⬡", font=("Segoe UI", 24),
                 bg=C["panel"], fg=C["accent"]).pack(side="left", padx=(0, 10))
        tk.Label(inner, text="CHMenuChanger",
                 font=FTT, bg=C["panel"], fg=C["text"]).pack(side="left")
        tk.Label(inner, text="  by JURMR",
                 font=("Segoe UI", 13), bg=C["panel"], fg=C["accent"]).pack(side="left", pady=(6,0))

    # -- Profile bar -----------------------------------------------------------

    def _build_profile_bar(self):
        f = tk.Frame(self, bg=C["card2"],
                     highlightbackground=C["border"], highlightthickness=1)
        f.pack(fill="x")
        inner = tk.Frame(f, bg=C["card2"], padx=14, pady=7)
        inner.pack(fill="x")

        tk.Label(inner, text="PROFILE:", font=FTB,
                 bg=C["card2"], fg=C["text_mid"]).pack(side="left")

        self._prof_var = tk.StringVar()
        self._prof_cb  = ttk.Combobox(inner, textvariable=self._prof_var,
                                       width=30, font=FT, state="readonly")
        self._prof_cb.pack(side="left", padx=8)
        self._prof_cb.bind("<<ComboboxSelected>>", self._on_profile_combo)

        def pbtn(label, cmd, bg=C["border"]):
            return tk.Button(inner, text=label, command=cmd,
                             bg=bg, fg=C["text"], relief="flat",
                             font=FT, padx=9, pady=3, cursor="hand2")

        pbtn("+ New",     self._profile_new).pack(side="left", padx=2)
        self._btn_rename = pbtn("Rename",    self._profile_rename)
        self._btn_rename.pack(side="left", padx=2)
        pbtn("Duplicate", self._profile_duplicate).pack(side="left", padx=2)
        self._btn_delete = pbtn("Delete",    self._profile_delete, bg="#3d1a1a")
        self._btn_delete.pack(side="left", padx=2)

        self._lock_lbl = tk.Label(inner, text="",
                                   font=FTS, bg=C["card2"], fg=C["warn"])
        self._lock_lbl.pack(side="left", padx=(10, 0))

        # Reminder to set default install in the launcher (right-aligned so it never gets clipped)
        tk.Label(inner,
                 text="ℹ  If backgrounds aren't saving, open the Launcher → Settings and set this install as your default.",
                 font=("Segoe UI", 8), bg=C["card2"], fg=C["text_dim"]).pack(side="right", padx=(14, 0))

        self._refresh_profile_combo()

    # -- GGM bar ---------------------------------------------------------------

    def _build_ggm_bar(self):
        f = tk.Frame(self, bg=C["card"],
                     highlightbackground=C["border"], highlightthickness=1)
        f.pack(fill="x")
        inner = tk.Frame(f, bg=C["card"], padx=14, pady=9)
        inner.pack(fill="x")

        tk.Label(inner, text="Clone Hero_Data folder:", font=FTB,
                 bg=C["card"], fg=C["text_mid"]).pack(side="left")
        self._data_v = tk.StringVar(value=_get_default_data())
        e = ttk.Entry(inner, textvariable=self._data_v,
                      width=56, font=FTM, style="DE.TEntry")
        e.pack(side="left", padx=8)
        tk.Button(inner, text="Browse…", command=self._browse_data,
                  bg=C["accent_dim"], fg=C["text"], relief="flat",
                  font=FT, padx=10, pady=3, cursor="hand2").pack(side="left", padx=2)
        tk.Button(inner, text="Load & Scan", command=self._load_ggm,
                  bg=C["accent"], fg="white", relief="flat",
                  font=FTB, padx=14, pady=3, cursor="hand2").pack(side="left", padx=2)

        # Backup status indicator - right-aligned
        self._backup_lbl = tk.Label(inner, text="",
                                     font=FTS, bg=C["card"], fg=C["text_dim"])
        self._backup_lbl.pack(side="right", padx=(0, 4))
        tk.Button(inner, text="Restore Backups", command=self._act_restore_backups,
                  bg=C["border"], fg=C["text_dim"], relief="flat",
                  font=FTS, padx=8, pady=2, cursor="hand2").pack(side="right", padx=4)

    def _build_main_area(self):
        main = tk.Frame(self, bg=C["bg"])
        main.pack(fill="both", expand=True, padx=10, pady=8)

        # sidebar
        side = tk.Frame(main, bg=C["panel"], width=218)
        side.pack(side="left", fill="y", padx=(0, 8))
        side.pack_propagate(False)

        tk.Label(side, text="BACKGROUNDS", font=("Segoe UI", 8, "bold"),
                 bg=C["panel"], fg=C["accent"], pady=7).pack(fill="x", padx=12)

        lf  = tk.Frame(side, bg=C["panel"])
        lf.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        vsb = ttk.Scrollbar(lf, orient="vertical")
        self._tree = ttk.Treeview(lf, selectmode="browse", show="tree",
                                   yscrollcommand=vsb.set, height=22)
        self._tree.column("#0", width=195)
        vsb.config(command=self._tree.yview)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        self._tiid = {}   # iid -> bg_name
        for bg in BACKGROUNDS:
            iid = self._tree.insert("", "end", text=f"  {bg}")
            self._tiid[iid] = bg
        self._tree.selection_set(list(self._tiid.keys())[0])

        # right side
        right = tk.Frame(main, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)

        # preview row
        prow = tk.Frame(right, bg=C["bg"])
        prow.pack(fill="both", expand=True)

        self._orig_card = self._make_bg_card(prow, "CURRENT  (in-game)", C["text_dim"])
        self._orig_card.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self._new_card  = self._make_bg_card(prow, "REPLACEMENT  (new)", C["accent2"])
        self._new_card.pack(side="left", fill="both", expand=True, padx=(5, 0))

        # controls
        ctrl = tk.Frame(right, bg=C["panel"], padx=14, pady=9)
        ctrl.pack(fill="x", pady=(8, 0))

        self._sel_lbl = tk.Label(ctrl, text="Selected: -",
                                  font=FTH, bg=C["panel"], fg=C["text"])
        self._sel_lbl.pack(side="left")
        self._req_lbl = tk.Label(ctrl, text="", font=FTS,
                                  bg=C["panel"], fg=C["text_dim"])
        self._req_lbl.pack(side="left", padx=(10, 0))

        br = tk.Frame(ctrl, bg=C["panel"])
        br.pack(side="right")
        def cb(t, cmd, bg=C["border"], fg=C["text"], bold=False):
            return tk.Button(br, text=t, command=cmd, bg=bg, fg=fg,
                             relief="flat", font=(FTB if bold else FT),
                             padx=11, pady=5, cursor="hand2")
        cb("▶ Export Original",     self._act_export_orig).pack(side="left", padx=3)
        cb("📂 Choose Replacement",  self._act_choose_replacement, C["accent_dim"]).pack(side="left", padx=3)
        cb("✖ Clear",                self._act_clear_replacement).pack(side="left", padx=3)
        self._apply_btn = cb("✔  Apply & Save",
                              self._act_apply_all, C["accent2"], "white", bold=True)
        self._apply_btn.pack(side="left", padx=3)

    def _make_bg_card(self, parent, label, label_fg):
        card = tk.Frame(parent, bg=C["card"],
                        highlightbackground=C["border"], highlightthickness=1)
        tk.Label(card, text=label, font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=label_fg, pady=5).pack(fill="x", padx=10)
        cv = tk.Canvas(card, bg=C["bg"], bd=0, highlightthickness=0, height=295)
        cv.pack(fill="both", expand=True, padx=6, pady=(0, 3))
        info = tk.Label(card, text="", font=FTS, bg=C["card"], fg=C["text_dim"])
        info.pack(pady=(0, 5))
        card._cv        = cv
        card._info      = info
        card._ph_text   = ""   # track current placeholder text for resize redraws
        cv.bind("<Configure>", lambda e, c=cv, k=card: self._on_bg_resize(c, k))
        # Don't draw placeholder at construction — canvas has no real size yet.
        # It will be drawn correctly on the first <Configure> event once laid out.
        return card

    def _build_statusbar(self):
        f = tk.Frame(self, bg=C["panel"], pady=5)
        f.pack(fill="x", side="bottom")
        tk.Label(f, textvariable=self._status_v, font=FTM,
                 bg=C["panel"], fg=C["text_mid"], padx=14).pack(side="left")

    # -- Profile management ----------------------------------------------------

    def _refresh_profile_combo(self):
        # Default profile always appears first in the dropdown
        names = sorted(self._profiles.keys(),
                       key=lambda n: (0 if n == DEFAULT_PROFILE_NAME else 1, n))
        self._prof_cb["values"] = names
        if self._active_name in names:
            self._prof_var.set(self._active_name)
        elif names:
            self._prof_var.set(names[0])

    def _on_profile_combo(self, _=None):
        n = self._prof_var.get()
        if n and n != self._active_name:
            self._switch_profile(n)

    def _switch_profile(self, name):
        if name not in self._profiles:
            return
        self._active_name = name
        self._active_prof = self._profiles[name]
        self._prof_var.set(name)
        self._cfg["last_profile"] = name
        _save_json(CONFIG_FILE, self._cfg)
        # sync ggm entry
        self._data_v.set(self._active_prof.get("data_path", _get_default_data()))
        # clear runtime state (new profile may have a different file)
        self._am = None
        self._asset_cache.clear()
        self._orig_pil.clear()
        self._new_pil.clear()
        self._orig_tk.clear()
        self._new_tk.clear()
        self._bg_refresh_tree()
        self._status("Profile: " + name)
        # Reset backup indicator
        if hasattr(self, "_backup_lbl"):
            self._backup_lbl.config(text="", fg=C["text_dim"])
        # Update lock state for Rename/Delete buttons
        if hasattr(self, "_btn_rename"):
            locked = self._is_default_profile(name)
            s  = "disabled" if locked else "normal"
            fg = C["text_dim"] if locked else C["text"]
            self._btn_rename.config(state=s, fg=fg)
            self._btn_delete.config(state=s, fg=fg)
            self._lock_lbl.config(
                text="🔒  Read-only" if locked else "")
        self._bg_refresh_panels()

    def _is_default_profile(self, name=None):
        """Return True if the named profile (or active profile) is the locked Default."""
        n = name if name is not None else self._active_name
        return n == DEFAULT_PROFILE_NAME or self._profiles.get(n, {}).get("locked", False)

    def _profile_new(self):
        name = simpledialog.askstring("New Profile", "Profile name:", parent=self)
        if not name or not name.strip():
            return
        name = name.strip()
        if name == DEFAULT_PROFILE_NAME:
            messagebox.showwarning("Reserved", "That name is reserved for the Default profile.")
            return
        if name in self._profiles:
            messagebox.showwarning("Exists", f"Profile '{name}' already exists.")
            return
        self._profiles[name] = _blank_profile(name)
        _save_profiles(self._profiles)
        self._refresh_profile_combo()
        self._switch_profile(name)

    def _profile_rename(self):
        old = self._active_name
        if not old:
            return
        if self._is_default_profile(old):
            messagebox.showwarning("Locked", "The Default profile cannot be renamed.")
            return
        name = simpledialog.askstring("Rename", f"Rename '{old}' to:",
                                       initialvalue=old, parent=self)
        if not name or not name.strip() or name.strip() == old:
            return
        name = name.strip()
        if name == DEFAULT_PROFILE_NAME:
            messagebox.showwarning("Reserved", "That name is reserved.")
            return
        if name in self._profiles:
            messagebox.showwarning("Exists", f"Profile '{name}' already exists.")
            return
        self._profiles[name] = self._profiles.pop(old)
        self._profiles[name]["name"] = name
        _save_profiles(self._profiles)
        self._active_name = name
        self._cfg["last_profile"] = name
        _save_json(CONFIG_FILE, self._cfg)
        self._refresh_profile_combo()

    def _profile_duplicate(self):
        src = self._active_name
        if not src:
            return
        default_name = "My Theme" if self._is_default_profile(src) else src + " Copy"
        name = simpledialog.askstring("Duplicate", f"Name for copy of '{src}':",
                                       initialvalue=default_name, parent=self)
        if not name or not name.strip():
            return
        name = name.strip()
        if name in self._profiles:
            messagebox.showwarning("Exists", f"Profile '{name}' already exists.")
            return
        self._profiles[name] = copy.deepcopy(self._profiles[src])
        self._profiles[name]["name"] = name
        self._profiles[name].pop("locked", None)   # copy is always editable
        _save_profiles(self._profiles)
        self._refresh_profile_combo()
        self._switch_profile(name)

    def _profile_delete(self):
        name = self._active_name
        if not name:
            return
        if self._is_default_profile(name):
            messagebox.showwarning("Locked", "The Default profile cannot be deleted.")
            return
        # Always keep at least Default + one user profile
        non_default = [n for n in self._profiles if not self._is_default_profile(n)]
        if len(non_default) <= 1:
            messagebox.showwarning("Cannot delete",
                "You must keep at least one profile besides Default.")
            return
        if not messagebox.askyesno("Delete Profile",
                                   f"Delete '{name}'? This cannot be undone."):
            return
        del self._profiles[name]
        _save_profiles(self._profiles)
        self._refresh_profile_combo()
        self._switch_profile(next(iter(self._profiles)))

    # -- GGM loading -----------------------------------------------------------

    def _browse_data(self):
        p = filedialog.askdirectory(
            title="Select Clone Hero_Data folder",
            initialdir=str(Path.home() / "Documents" / "Clone Hero"))
        if p:
            self._data_v.set(p)

    def _load_ggm(self):
        path = self._data_v.get().strip()
        if not os.path.isdir(path):
            messagebox.showerror("Not found",
                "Folder not found:\n" + path +
                "\n\nPlease select your Clone Hero_Data folder.")
            return

        # Don't overwrite data_path on the locked Default profile
        if not self._is_default_profile():
            self._active_prof["data_path"] = path
            _save_profiles(self._profiles)
        self._status("Scanning " + path + " ...")
        self.update_idletasks()

        def worker():
            try:
                am = AssetManager(path)
                needs = am.needs_backup()
                if needs:
                    created, bk_errors = am.create_backups()
                    if bk_errors:
                        self.after(0, lambda: messagebox.showwarning(
                            "Backup warning",
                            "Some files could not be backed up:\n\n" +
                            "\n".join(bk_errors) +
                            "\n\nProceed with caution."))
                self.after(0, lambda: self._on_ggm_ready(am))
            except Exception as ex:
                msg = str(ex)
                self.after(0, lambda: (
                    self._status("Load error: " + msg),
                    messagebox.showerror(
                        "Load Error",
                        "Could not scan folder:\n\n" + msg +
                        "\n\nMake sure you selected the Clone Hero_Data folder.")
                ))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ggm_ready(self, am):
        self._am = am
        self._asset_cache.clear()
        self._orig_pil.clear()
        self._orig_tk.clear()
        all_names = am.texture_names()
        for bg in BACKGROUNDS:
            self._asset_cache[bg] = am.find_for_bg(bg)
        found = sum(1 for v in self._asset_cache.values() if v is not None)

        backed_up = am.has_full_backup()
        self._update_backup_indicator(backed_up, am)
        bk_note = "  ✓ Backups ready." if backed_up else "  ⚠ Creating backups…"
        self._status(
            "Scanned {} - {} textures, {}/{} backgrounds matched.{}".format(
                Path(am.data_dir).name, len(all_names), found, len(BACKGROUNDS), bk_note
            )
        )
        self._bg_refresh_tree()
        self._bg_refresh_panels()


    # -- Tree refresh ----------------------------------------------------------

    def _bg_refresh_tree(self):
        reps = self._active_prof.get("replacements", {})
        for iid, bg in self._tiid.items():
            has_rep = bool(reps.get(bg) and os.path.isfile(reps[bg]))
            matched  = self._asset_cache.get(bg) is not None
            if has_rep and matched:
                icon = "✎ "
            elif has_rep and not matched:
                icon = "⚠ "
            else:
                icon = "  "
            self._tree.item(iid, text=f"{icon}{bg}")

    def _selected_bg(self):
        sel = self._tree.selection()
        if sel:
            return self._tiid.get(sel[0], BACKGROUNDS[0])
        return BACKGROUNDS[0]

    def _on_tree_select(self, _=None):
        bg = self._selected_bg()
        w, h   = required_size(bg)
        exact  = exact_match_required(bg)
        self._sel_lbl.config(text=f"Selected: {bg}")
        self._req_lbl.config(
            text=f"{'Exact' if exact else 'Min'}: {w}×{h}")
        self._bg_refresh_panels()

    # -- Preview panels --------------------------------------------------------

    def _bg_refresh_panels(self):
        bg = self._selected_bg()

        # -- orig --------------------------------------------------------------
        if bg in self._orig_pil:
            self._orig_card._ph_text = ""
            self._bg_put_image(self._orig_card, self._orig_pil[bg], "orig", bg)
        elif self._am is not None:
            an = self._asset_cache.get(bg)
            if an:
                self._bg_placeholder(self._orig_card._cv, "Loading\u2026")
                self._orig_card._info.config(text="")
                am = self._am
                def _load(am=am, bg=bg, an=an):
                    img, err = am.export_image(an)
                    self.after(0, lambda: self._on_orig_ready(bg, an, img, err))
                threading.Thread(target=_load, daemon=True).start()
            else:
                self._bg_placeholder(self._orig_card._cv,
                                     "No Texture2D matched for '{}'".format(bg))
                self._orig_card._info.config(text="")
        else:
            self._bg_placeholder(self._orig_card._cv,
                                 "Select and scan a Clone Hero_Data folder first.")
            self._orig_card._info.config(text="")

        # -- new ---------------------------------------------------------------
        reps     = self._active_prof.get("replacements", {})
        rep_path = reps.get(bg, "")
        if bg in self._new_pil:
            self._new_card._ph_text = ""
            self._bg_put_image(self._new_card, self._new_pil[bg], "new", bg)
        elif rep_path and os.path.isfile(rep_path):
            try:
                img = Image.open(rep_path).convert("RGBA")
                self._new_pil[bg] = img
                self._new_card._ph_text = ""
                self._bg_put_image(self._new_card, img, "new", bg)
                w, h = img.size
                self._new_card._info.config(
                    text=f"{w}\u00d7{h}  |  {Path(rep_path).name}",
                    fg=C["success"])
            except Exception:
                self._bg_placeholder(self._new_card._cv,
                                     "Could not load replacement image")
                self._new_card._info.config(text="")
        else:
            self._bg_placeholder(self._new_card._cv, "No replacement selected")
            self._new_card._info.config(text="")

    def _on_orig_ready(self, bg, asset_name, img, err=None):
        if img:
            self._orig_pil[bg] = img
            if self._selected_bg() == bg:
                self._bg_put_image(self._orig_card, img, "orig", bg)
                w, h = img.size
                self._orig_card._info.config(
                    text=f"{w}×{h}  |  {asset_name}", fg=C["text_mid"])
        else:
            if self._selected_bg() == bg:
                short_err = (err or "unknown error")[:300]
                self._bg_placeholder(self._orig_card._cv,
                                     f"Could not decode '{asset_name}'\n{short_err}")
                self._orig_card._info.config(
                    text="Decode failed", fg=C["error"])

    def _bg_put_image(self, card, pil, key, bg):
        cv = card._cv
        cv.update_idletasks()
        cw = cv.winfo_width()  or 520
        ch = cv.winfo_height() or 295
        ph = pil.copy()
        ph.thumbnail((cw - 10, ch - 10), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(ph)
        cv.delete("all")
        cv.create_rectangle(0, 0, cw, ch, fill=C["bg"], outline="")
        cv.create_image(cw // 2, ch // 2, image=tk_img, anchor="center")
        (self._orig_tk if key == "orig" else self._new_tk)[bg] = tk_img

    def _on_bg_resize(self, cv, card):
        bg = self._selected_bg()
        if card is self._orig_card and bg in self._orig_pil:
            self._bg_put_image(self._orig_card, self._orig_pil[bg], "orig", bg)
        elif card is self._new_card and bg in self._new_pil:
            self._bg_put_image(self._new_card, self._new_pil[bg], "new", bg)
        else:
            # Redraw placeholder at the new correct canvas size
            ph = getattr(card, "_ph_text", "")
            if ph:
                self._bg_placeholder(cv, ph)
            else:
                self._bg_refresh_panels()

    def _bg_placeholder(self, cv: tk.Canvas, text: str):
        cv.update_idletasks()
        w = cv.winfo_width()
        h = cv.winfo_height()
        if w < 20: w = 520
        if h < 20: h = 295
        cv.delete("all")
        cv.create_rectangle(1, 1, w-1, h-1, outline=C["border"], fill=C["bg"])
        cv.create_text(w//2, h//2, text=text, fill=C["text_dim"], font=FT, width=w-40)
        # Remember the text on the card for resize redraws
        for card in (self._orig_card, self._new_card):
            if hasattr(card, "_cv") and card._cv is cv:
                card._ph_text = text
                break

    def _placeholder(self, cv: tk.Canvas, text: str):
        cv.delete("all")
        cv.update_idletasks()
        w = cv.winfo_width()  or 520
        h = cv.winfo_height() or 295
        cv.create_rectangle(1, 1, w-1, h-1, outline=C["border"], fill=C["bg"])
        cv.create_text(w//2, h//2, text=text, fill=C["text_dim"],
                       font=FT, width=w-40)

    # -- Action buttons --------------------------------------------------------

    def _act_export_orig(self):
        if self._am is None:
            messagebox.showwarning("No folder", "Select and scan a Clone Hero_Data folder first.")
            return
        bg = self._selected_bg()
        an = self._asset_cache.get(bg)
        if not an:
            messagebox.showwarning("Not found",
                                   f"No texture matched for '{bg}'.")
            return
        out = filedialog.asksaveasfilename(
            title=f"Export '{bg}' as PNG",
            defaultextension=".png",
            initialfile=f"{bg.replace(' ','_')}_original.png",
            filetypes=[("PNG", "*.png")])
        if not out:
            return
        img = self._orig_pil.get(bg)
        if img is None:
            img, err = self._am.export_image(an)
        else:
            err = None
        if img:
            img.save(out)
            self._status(f"Exported: {out}")
            messagebox.showinfo("Exported", f"Saved to:\n{out}")
        else:
            messagebox.showerror("Export failed",
                "Could not decode texture.\n\n" + (err or "unknown error"))

    def _act_choose_replacement(self):
        if self._is_default_profile():
            answer = messagebox.askyesno(
                "Create a profile first",
                "The Default profile is read-only.\n\n"
                "Create a new profile to set replacement images?")
            if answer:
                self._profile_new()
            return
        bg   = self._selected_bg()
        path = filedialog.askopenfilename(
            title=f"Choose replacement for '{bg}'",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tga"),
                       ("All", "*")])
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Image error", f"Cannot open:\n{e}")
            return
        iw, ih = img.size
        rw, rh = required_size(bg)
        if exact_match_required(bg):
            if iw != rw or ih != rh:
                messagebox.showerror(
                    "Wrong size",
                    f"'{bg}' requires exactly {rw}×{rh} px.\n"
                    f"Your image is {iw}×{ih}.")
                return
        else:
            if iw < rw or ih < rh:
                messagebox.showerror(
                    "Too small",
                    f"'{bg}' needs at least {rw}×{rh} px.\n"
                    f"Your image is only {iw}×{ih}.")
                return
        reps = self._active_prof.setdefault("replacements", {})
        reps[bg] = path
        _save_profiles(self._profiles)
        self._new_pil[bg] = img
        self._new_tk.pop(bg, None)
        self._bg_put_image(self._new_card, img, "new", bg)
        self._new_card._info.config(
            text=f"{iw}×{ih}  ✓  |  {Path(path).name}", fg=C["success"])
        self._bg_refresh_tree()
        self._status(f"Replacement set for '{bg}'.")

    def _act_clear_replacement(self):
        if self._is_default_profile():
            return
        bg   = self._selected_bg()
        self._active_prof.get("replacements", {}).pop(bg, None)
        _save_profiles(self._profiles)
        self._new_pil.pop(bg, None)
        self._new_tk.pop(bg, None)
        self._bg_placeholder(self._new_card._cv, "No replacement selected")
        self._new_card._info.config(text="")
        self._bg_refresh_tree()
        self._status(f"Cleared replacement for '{bg}'.")

    def _act_apply_all(self):
        if self._am is None:
            messagebox.showwarning("No folder",
                "Select and scan a Clone Hero_Data folder first.")
            return
        if self._is_default_profile():
            if messagebox.askyesno("Create a profile first",
                    "You are on the read-only Default profile.\nCreate a new profile now?"):
                self._profile_new()
            return
        reps = self._active_prof.get("replacements", {})
        if not reps:
            messagebox.showwarning("Nothing to apply",
                "Set at least one replacement image first.")
            return
        if not self._am.has_full_backup():
            messagebox.showerror("No backup",
                "Backups have not been created yet.\nReload the folder to trigger backup creation.")
            return
        summary = []; skipped = []
        for bg, img_path in reps.items():
            an       = self._asset_cache.get(bg)
            src_file = self._am.source_file(an) if an else None
            if an and os.path.isfile(img_path):
                label = Path(src_file).name if src_file else "?"
                summary.append("  {}  ->  {}  ({})".format(bg, Path(img_path).name, label))
            else:
                reason = "texture not found" if not an else "image file missing"
                skipped.append("  {}  ({})".format(bg, reason))
        if not summary:
            messagebox.showwarning("Nothing applicable",
                "None of the replacements can be applied.\n\n" + "\n".join(skipped))
            return
        msg = "\n".join(summary)
        if skipped: msg += "\n\nSkipped:\n" + "\n".join(skipped)
        if not messagebox.askyesno("Apply & Save in-place",
                "Apply these replacements directly to Clone Hero_Data:\n\n" +
                msg + "\n\nOriginals are backed up in _CH_BG_Backups.\nProceed?"):
            return
        self._status("Applying\u2026"); self.update_idletasks()
        self._apply_btn.config(state="disabled")

        def worker():
            errors = []; applied = 0
            for bg, img_path in reps.items():
                an = self._asset_cache.get(bg)
                if not an: errors.append(f"'{bg}': no matching texture found"); continue
                if not os.path.isfile(img_path): errors.append(f"'{bg}': image missing"); continue
                try:
                    pil = Image.open(img_path).convert("RGBA")
                    ok  = self._am.import_image(an, pil)
                    if ok: applied += 1
                    else: errors.append(f"'{bg}': import_image returned False")
                except Exception as ex:
                    errors.append(f"'{bg}': {ex}")
            if applied == 0:
                def fail():
                    self._apply_btn.config(state="normal")
                    self._status("Apply failed.")
                    messagebox.showerror("Apply failed",
                        "No textures could be written.\n\nErrors:\n" + "\n".join(errors))
                self.after(0, fail); return
            saved, save_errors = self._am.save_modified()
            errors.extend(save_errors)
            def done():
                self._apply_btn.config(state="normal")
                if saved:
                    file_list = "\n".join("  " + Path(p).name for p in saved)
                    extra = ("\n\nWarnings:\n" + "\n".join(errors)) if errors else ""
                    self._status("{} texture(s) applied in-place.".format(applied))
                    messagebox.showinfo("Done!",
                        "Applied {} texture(s).\n\nModified:\n{}\n\n"
                        "Restart Clone Hero to see the changes.{}".format(
                            applied, file_list, extra))
                    self._orig_pil.clear(); self._orig_tk.clear()
                else:
                    self._status("Save FAILED.")
                    messagebox.showerror("Save failed",
                        "Textures were patched but could not be saved.\n\n" +
                        "\n".join(errors))
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


    def _update_backup_indicator(self, backed_up, am=None):
        """Update the backup status label in the GGM bar."""
        if backed_up:
            bd_name = am.BACKUP_DIR_NAME if am else "_CH_BG_Backups"
            self._backup_lbl.config(
                text="✓ Backups in " + bd_name,
                fg=C["success"])
        else:
            self._backup_lbl.config(
                text="⚠ No backups yet",
                fg=C["warn"])

    def _act_restore_backups(self):
        """Copy all backup files back over the originals in Clone Hero_Data."""
        if self._am is None:
            messagebox.showwarning("No folder",
                "Load a Clone Hero_Data folder first.")
            return
        bd = self._am.backup_dir()
        if not os.path.isdir(bd):
            messagebox.showinfo("No backups",
                "No backup folder found at:\n" + bd)
            return

        backup_files = [f for f in Path(bd).iterdir() if f.is_file()]
        if not backup_files:
            messagebox.showinfo("No backups", "Backup folder is empty.")
            return

        names = "\n".join("  " + f.name for f in backup_files)
        if not messagebox.askyesno("Restore backups",
                "This will overwrite the current files in Clone Hero_Data "
                "with the originals from the backup folder:\n\n" +
                names + "\n\nProceed?"):
            return

        errors = []
        restored = []
        for bk in backup_files:
            dest = Path(self._am.data_dir) / bk.name
            try:
                shutil.copy2(str(bk), str(dest))
                restored.append(bk.name)
            except Exception as e:
                errors.append("{}: {}".format(bk.name, e))

        if errors:
            messagebox.showerror("Restore errors",
                "Some files could not be restored:\n\n" +
                "\n".join(errors))
        else:
            self._status("Restored {} file(s) from backup.".format(len(restored)))
            messagebox.showinfo("Restored",
                "Restored {} file(s) from backup.\n\n"
                "Reload the folder to continue editing.".format(len(restored)))
            # Clear preview cache and reload from the restored originals
            self._orig_pil.clear()
            self._orig_tk.clear()
            self._am = None
            self._asset_cache.clear()
            if hasattr(self, "_backup_lbl"):
                self._backup_lbl.config(text="", fg=C["text_dim"])
            self._load_ggm()

    def _status(self, msg):
        self._status_v.set(msg)
        self.update_idletasks()

    def _on_close(self):
        _save_json(CONFIG_FILE, self._cfg)
        _save_profiles(self._profiles)
        self.destroy()


# -- Entry point ---------------------------------------------------------------

def main():
    # PyInstaller --windowed already suppresses the console in compiled exes.
    # When running as a plain .py on Windows, hide the console window.
    if not getattr(sys, "frozen", False) and sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.user32.ShowWindow(
                ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except Exception:
            pass

    App().mainloop()


if __name__ == "__main__":
    main()