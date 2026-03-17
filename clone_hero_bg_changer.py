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
    accent="#6c3bff", accent_dim="#3d2299", accent2="#ff3b8a",
    text="#e9ecf8", text_dim="#636b82", text_mid="#9aa3bf",
    success="#22c55e", warn="#f59e0b", error="#ef4444",
    selected="#341a7a", hover="#262d42",
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
            _logged_attrs = False  # log Texture2D attrs once per file
            for obj in env.objects:
                if obj.type.name == "Texture2D":
                    try:
                        d = obj.read()
                        n = getattr(d, "m_Name", None) or getattr(d, "name", None)
                        if n and n not in self._data:
                            self._data[n]    = d
                            self._env_map[n] = (env, key)
                            count += 1
                            # Log attrs of first texture so we know the real names
                            if not _logged_attrs:
                                _logged_attrs = True
                                attrs = [a for a in dir(d) if not a.startswith("__")]
                                _log("  [attrs] first Texture2D in {}: {}".format(
                                    Path(fpath).name, attrs))
                                # Log stream data info if present
                                for sd_attr in ("m_StreamData", "streamData",
                                                "stream_data", "m_imageData"):
                                    val = getattr(d, sd_attr, None)
                                    if val is not None:
                                        _log("  [stream] {}.{} = {}".format(
                                            n, sd_attr, repr(val)[:200]))
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
            _log("[import_image] not in cache: {}".format(asset_name))
            return False

        rgba = pil.convert("RGBA")
        # NOTE: do NOT flip here -- set_image() handles Unity's bottom-up
        # storage format internally. Flipping here would double-flip it.

        import traceback

        # Try set_image() first (UnityPy 1.20+ API, avoids the dynlib loader
        # that pulls in FMOD and crashes in frozen exes)
        try:
            if hasattr(d, "set_image"):
                d.set_image(rgba)
                d.save()
                self._dirty.add(asset_name)
                _log("[WRITE OK] set_image: {}".format(asset_name))
                return True
        except Exception as e:
            _log("[WRITE FAIL] set_image for \'{}\': {}".format(asset_name, e))
            _log("[WRITE FAIL] traceback:\n" + traceback.format_exc())

        # Fallback: property setter (works in script mode)
        try:
            d.image = rgba
            d.save()
            self._dirty.add(asset_name)
            _log("[WRITE OK] image= setter: {}".format(asset_name))
            return True
        except Exception as e:
            _log("[WRITE FAIL] image= setter for \'{}\': {}".format(asset_name, e))
            _log("[WRITE FAIL] traceback:\n" + traceback.format_exc())
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
                # env.file is the SerializedFile for this specific .assets file.
                # Calling .save() returns the bytes for that file only.
                data = env.file.save()
                with open(fpath, "wb") as f:
                    f.write(data)
                print("[save] {} ok - {} bytes".format(fname, len(data)))
                saved.append(fpath)
            except Exception as e:
                print("[save] {} FAILED: {}".format(fname, e))
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
                print("[reload]", Path(fpath).name, e)
        self._dirty.clear()


# -- Profile helpers -----------------------------------------------------------

def _blank_profile(name):
    return {"name": name, "data_path": DEFAULT_DATA, "replacements": {}}

def _load_profiles():
    d = _load_json(PROFILES_FILE, {})
    return d if isinstance(d, dict) else {}

def _save_profiles(p):
    _save_json(PROFILES_FILE, p)


# -- Setup dialog (first launch) -----------------------------------------------


# -- Welcome / info dialog ------------------------------------------------------

class WelcomeDialog:
    """
    Shown on first launch. Explains the Clone Hero launcher issue and
    JURMR branding. Never shown again once dismissed.
    """

    def __init__(self, root: tk.Tk):
        self.win = tk.Toplevel(root)
        self.win.title("Welcome to CHMenuChanger")
        self.win.configure(bg=C["bg"])
        self.win.resizable(False, False)
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)

        # Header
        hdr = tk.Frame(self.win, bg=C["panel"])
        hdr.pack(fill="x")
        hi  = tk.Frame(hdr, bg=C["panel"], padx=28, pady=18)
        hi.pack(fill="x")

        tk.Label(hi, text="CHMenuChanger", font=("Segoe UI", 22, "bold"),
                 bg=C["panel"], fg=C["text"]).pack(side="left")
        tk.Label(hi, text="  by JURMR", font=("Segoe UI", 13),
                 bg=C["panel"], fg=C["accent"]).pack(side="left", pady=(8, 0))

        # Body
        body = tk.Frame(self.win, bg=C["bg"], padx=28, pady=20)
        body.pack(fill="both")

        # Info card - launcher warning
        card = tk.Frame(body, bg=C["card"],
                        highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="x", pady=(0, 14))
        ci   = tk.Frame(card, bg=C["card"], padx=18, pady=16)
        ci.pack(fill="x")

        tk.Label(ci, text="! Important - Clone Hero Launcher",
                 font=FTB, bg=C["card"], fg=C["warn"]).pack(anchor="w")

        msg = (
            "The Clone Hero launcher resets your game files back to default after "
            "every single launch, which will undo any background changes made with "
            "this tool.\n\n"
            "To prevent this, you need to set up your install manually:\n\n"
            "  1.  Install Clone Hero through the launcher as normal.\n"
            "  2.  Move that install folder to a different location on your PC.\n"
            "  3.  In the launcher settings, remove the old install path.\n"
            "  4.  Add your new manual path instead.\n\n"
            "Once set up this way, the launcher will no longer overwrite your files.\n\n"
            "Note: A workaround that avoids this setup entirely is being worked on "
            "for a future update."
        )
        tk.Label(ci, text=msg, font=FT, bg=C["card"], fg=C["text_mid"],
                 justify="left", wraplength=520).pack(anchor="w", pady=(8, 0))

        # Footer
        foot = tk.Frame(self.win, bg=C["panel"], padx=24, pady=14)
        foot.pack(fill="x")
        tk.Label(foot, text="Made by JURMR", font=FTS,
                 bg=C["panel"], fg=C["text_dim"]).pack(side="left")
        tk.Button(foot, text="Got it, let's go  ->",
                  command=self.win.destroy,
                  bg=C["accent"], fg="white", relief="flat",
                  font=FTB, padx=18, pady=6,
                  cursor="hand2").pack(side="right")

        # Center on root
        self.win.update_idletasks()
        rw = root.winfo_width()  or 800
        rh = root.winfo_height() or 600
        rx = root.winfo_rootx()
        ry = root.winfo_rooty()
        dw = self.win.winfo_reqwidth()
        dh = self.win.winfo_reqheight()
        self.win.geometry("+{}+{}".format(rx + (rw - dw)//2, ry + (rh - dh)//2))


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
        # Always enforce: locked, no replacements
        self._profiles[DEFAULT_PROFILE_NAME]["locked"] = True
        self._profiles[DEFAULT_PROFILE_NAME]["replacements"] = {}
        _save_profiles(self._profiles)

        last = self._cfg.get("last_profile", "")
        if last and last in self._profiles:
            self._switch_profile(last)
        elif self._profiles:
            self._switch_profile(next(iter(self._profiles)))

        # Show welcome dialog on first launch
        if not self._cfg.get("welcome_shown", False):
            self._cfg["welcome_shown"] = True
            _save_json(CONFIG_FILE, self._cfg)
            dlg = WelcomeDialog(self)
            self.wait_window(dlg.win)

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
        self._data_v = tk.StringVar(value=DEFAULT_DATA)
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

        self._orig_card = self._make_card(prow, "CURRENT  (in-game)", C["text_dim"])
        self._orig_card.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self._new_card  = self._make_card(prow, "REPLACEMENT  (new)", C["accent2"])
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

    def _make_card(self, parent, label, label_fg):
        card = tk.Frame(parent, bg=C["card"],
                        highlightbackground=C["border"], highlightthickness=1)
        tk.Label(card, text=label, font=("Segoe UI", 9, "bold"),
                 bg=C["card"], fg=label_fg, pady=5).pack(fill="x", padx=10)
        cv = tk.Canvas(card, bg=C["bg"], bd=0, highlightthickness=0, height=295)
        cv.pack(fill="both", expand=True, padx=6, pady=(0, 3))
        info = tk.Label(card, text="", font=FTS, bg=C["card"], fg=C["text_dim"])
        info.pack(pady=(0, 5))
        card._cv   = cv
        card._info = info
        cv.bind("<Configure>", lambda e, c=cv, k=card: self._on_resize(c, k))
        self._placeholder(cv, "-")
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
        self._data_v.set(self._active_prof.get("data_path", DEFAULT_DATA))
        # clear runtime state (new profile may have a different file)
        self._am = None
        self._asset_cache.clear()
        self._orig_pil.clear()
        self._new_pil.clear()
        self._orig_tk.clear()
        self._new_tk.clear()
        self._refresh_tree()
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
                text="🔒  Read-only  -  this is the original backup" if locked else "")
        self._refresh_panels()

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

                # -- Auto-backup any files not yet backed up ----------------
                needs = am.needs_backup()
                if needs:
                    created, bk_errors = am.create_backups()
                    if bk_errors:
                        self.after(0, lambda: messagebox.showwarning(
                            "Backup warning",
                            "Some files could not be backed up:\n\n" +
                            "\n".join(bk_errors) +
                            "\n\nProceed with caution."))
                    else:
                        names = ", ".join(Path(p).name for p in created)
                        print("[backup] created:", names)

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
        self._refresh_tree()
        self._refresh_panels()


    # -- Tree refresh ----------------------------------------------------------

    def _refresh_tree(self):
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
        self._refresh_panels()

    # -- Preview panels --------------------------------------------------------

    def _refresh_panels(self):
        bg = self._selected_bg()

        # -- orig --------------------------------------------------------------
        if bg in self._orig_pil:
            self._put_image(self._orig_card, self._orig_pil[bg], "orig", bg)
        elif self._am is not None:
            an = self._asset_cache.get(bg)
            if an:
                self._placeholder(self._orig_card._cv, "Loading…")
                self._orig_card._info.config(text="")
                am = self._am
                def _load(am=am, bg=bg, an=an):
                    img, err = am.export_image(an)
                    self.after(0, lambda: self._on_orig_ready(bg, an, img, err))
                threading.Thread(target=_load, daemon=True).start()
            else:
                self._placeholder(self._orig_card._cv,
                                  "No Texture2D matched for '{}'".format(bg))
                self._orig_card._info.config(text="")
        else:
            self._placeholder(self._orig_card._cv,
                              "Select and scan a Clone Hero_Data folder first.")
            self._orig_card._info.config(text="")

        # -- new ---------------------------------------------------------------
        reps     = self._active_prof.get("replacements", {})
        rep_path = reps.get(bg, "")
        if bg in self._new_pil:
            self._put_image(self._new_card, self._new_pil[bg], "new", bg)
        elif rep_path and os.path.isfile(rep_path):
            try:
                img = Image.open(rep_path).convert("RGBA")
                self._new_pil[bg] = img
                self._put_image(self._new_card, img, "new", bg)
                w, h = img.size
                self._new_card._info.config(
                    text=f"{w}×{h}  |  {Path(rep_path).name}",
                    fg=C["success"])
            except Exception:
                self._placeholder(self._new_card._cv,
                                  "Could not load replacement image")
                self._new_card._info.config(text="")
        else:
            self._placeholder(self._new_card._cv, "No replacement selected")
            self._new_card._info.config(text="")

    def _on_orig_ready(self, bg, asset_name, img, err=None):
        if img:
            self._orig_pil[bg] = img
            if self._selected_bg() == bg:
                self._put_image(self._orig_card, img, "orig", bg)
                w, h = img.size
                self._orig_card._info.config(
                    text=f"{w}×{h}  |  {asset_name}", fg=C["text_mid"])
        else:
            if self._selected_bg() == bg:
                # Show the real decode error so it\'s visible in the UI
                short_err = (err or "unknown error")[:300]
                self._placeholder(self._orig_card._cv,
                                  f"Could not decode \'{asset_name}\'\n{short_err}")
                self._orig_card._info.config(
                    text="Decode failed -- see above", fg=C["error"])

    def _put_image(self, card, pil, key, bg):
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

    def _on_resize(self, cv, card):
        bg = self._selected_bg()
        if card is self._orig_card and bg in self._orig_pil:
            self._put_image(self._orig_card, self._orig_pil[bg], "orig", bg)
        elif card is self._new_card and bg in self._new_pil:
            self._put_image(self._new_card, self._new_pil[bg], "new", bg)

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
        self._put_image(self._new_card, img, "new", bg)
        self._new_card._info.config(
            text=f"{iw}×{ih}  ✓  |  {Path(path).name}", fg=C["success"])
        self._refresh_tree()
        self._status(f"Replacement set for '{bg}'.")

    def _act_clear_replacement(self):
        if self._is_default_profile():
            return  # Default profile has no replacements to clear
        bg   = self._selected_bg()
        reps = self._active_prof.get("replacements", {})
        reps.pop(bg, None)
        _save_profiles(self._profiles)
        self._new_pil.pop(bg, None)
        self._new_tk.pop(bg, None)
        self._placeholder(self._new_card._cv, "No replacement selected")
        self._new_card._info.config(text="")
        self._refresh_tree()
        self._status(f"Cleared replacement for '{bg}'.")

    def _act_apply_all(self):
        if self._am is None:
            messagebox.showwarning("No folder",
                "Select and scan a Clone Hero_Data folder first.")
            return
        # Block saving from the Default profile
        if self._is_default_profile():
            answer = messagebox.askyesno(
                "Create a profile first",
                "You are on the read-only Default profile.\n\n"
                "You must save your changes to a named profile.\n\n"
                "Create a new profile now?")
            if answer:
                self._profile_new()
            return
        reps = self._active_prof.get("replacements", {})
        if not reps:
            messagebox.showwarning("Nothing to apply",
                "Set at least one replacement image first.")
            return

        # Safety: backups must exist before we overwrite anything in-place
        if not self._am.has_full_backup():
            messagebox.showerror("No backup",
                "Backups have not been created yet.\n\n"
                "Reload the folder to trigger automatic backup creation.")
            return

        summary = []
        skipped = []
        for bg, img_path in reps.items():
            an       = self._asset_cache.get(bg)
            src_file = self._am.source_file(an) if an else None
            if an and os.path.isfile(img_path):
                label = Path(src_file).name if src_file else "?"
                summary.append("  {}  ->  {}  ({})".format(
                    bg, Path(img_path).name, label))
            else:
                reason = "texture not found" if not an else "image file missing"
                skipped.append("  {}  ({})".format(bg, reason))

        if not summary:
            messagebox.showwarning("Nothing applicable",
                "None of the replacements can be applied.\n\n" +
                "\n".join(skipped))
            return

        msg = "\n".join(summary)
        if skipped:
            msg += "\n\nSkipped:\n" + "\n".join(skipped)

        if not messagebox.askyesno("Apply & Save in-place",
                "Apply these replacements directly to Clone Hero_Data:\n\n" +
                msg + "\n\nOriginals are backed up in _CH_BG_Backups.\nProceed?"):
            return

        self._status("Applying...")
        self.update_idletasks()
        self._apply_btn.config(state="disabled")

        def worker():
            errors  = []
            applied = 0
            _log("\n=== WRITE SESSION START ({} replacements) ===".format(len(reps)))
            for bg, img_path in reps.items():
                an = self._asset_cache.get(bg)
                if not an:
                    errors.append("'{}': no matching texture found".format(bg))
                    continue
                if not os.path.isfile(img_path):
                    errors.append("'{}': image missing".format(bg))
                    continue
                try:
                    pil = Image.open(img_path).convert("RGBA")
                    ok  = self._am.import_image(an, pil)
                    if ok:
                        applied += 1
                    else:
                        errors.append("'{}': import_image returned False".format(bg))
                except Exception as ex:
                    errors.append("'{}': {}".format(bg, ex))

            if applied == 0:
                def fail():
                    self._apply_btn.config(state="normal")
                    self._status("Apply failed.")
                    messagebox.showerror("Apply failed",
                        "No textures could be written.\n\nErrors:\n" +
                        "\n".join(errors))
                self.after(0, fail)
                return

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
                    # Clear orig preview cache so it reloads fresh next time
                    self._orig_pil.clear()
                    self._orig_tk.clear()
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
