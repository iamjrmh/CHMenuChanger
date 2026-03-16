# 🎨 CHMenuChanger by JURMR

Swap out Clone Hero's menu background textures without touching a single config file. Built on top of UnityPy for direct asset editing — no UABEA CLI required.

[![Platform](https://img.shields.io/badge/platform-Windows-blue)](https://github.com/iamjrmh/CHMenuChanger)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/iamjrmh/CHMenuChanger)

---

## ⚠️ Important - Clone Hero Launcher

The Clone Hero launcher **resets your game files back to default after every launch**, which will undo any background changes made with this tool.

To prevent that, you need to set up your install manually:

1. Install Clone Hero through the launcher as normal.
2. Move that install folder to a different location on your PC.
3. In the launcher settings, remove the old install path.
4. Add your new manual path instead.

Once set up this way, the launcher will no longer overwrite your files. A workaround that avoids this setup entirely is being worked on for a future update.

---

## ✨ Features

- **Direct asset editing** - reads and writes Unity `.assets` files using UnityPy, no external tools needed
- **16 supported backgrounds** - all standard menu backgrounds plus the logo
- **Live preview** - see the current in-game texture and your replacement side by side before applying
- **Auto backup** - original files are automatically backed up to `_CH_BG_Backups` on first scan, one time
- **One-click restore** - revert to originals at any time from the Restore Backups button
- **Profile system** - save multiple background sets and switch between them freely
- **Default profile** - read-only profile that always reflects the original unmodified textures
- **Size validation** - enforces minimum resolution requirements per background (1920x1080 standard, 2030x1328 for the logo)
- **No install required** - distributed as a standalone `.exe`, just download and run

---

## 🚀 Quick Start

1. Go to the **Releases** page on this GitHub repository and download **CHMenuChanger.zip** from the latest release.
2. Extract the ZIP anywhere on your PC — your Desktop, a games folder, wherever you like.
3. Double-click **CHMenuChanger.exe** to launch. No install, no Python, nothing else needed.
4. Click **Browse** and select your `Clone Hero_Data` folder (usually at `Documents\Clone Hero\Clone Hero_Data`).
5. Click **Load & Scan** — the tool scans all asset files and creates backups automatically.
6. Select a background from the left panel.
7. Click **Choose Replacement** and pick your image.
8. Click **Apply & Save** to write the changes directly to your game files.
9. Restart Clone Hero to see the result.

---

## 🖼️ Supported Backgrounds

| Name | Min Size | Source File |
|---|---|---|
| Black | 1920x1080 | sharedassets1.assets |
| Spray | 1920x1080 | sharedassets1.assets |
| Pastel Burst | 1920x1080 | sharedassets1.assets |
| Groovy | 1920x1080 | sharedassets1.assets |
| Grains | 1920x1080 | sharedassets1.assets |
| Blue Rays | 1920x1080 | sharedassets1.assets |
| Alien | 1920x1080 | sharedassets1.assets |
| Autumn | 1920x1080 | sharedassets1.assets |
| Light | 1920x1080 | sharedassets1.assets |
| Dark | 1920x1080 | sharedassets1.assets |
| Classic | 1920x1080 | sharedassets1.assets |
| Surfer | 1920x1080 | sharedassets1.assets |
| SurferAlt | 1920x1080 | sharedassets1.assets |
| Rainbow | 1920x1080 | sharedassets1.assets |
| Animated | 1920x1080 | sharedassets1.assets |
| Logo_Transparent | 2030x1328 exact | globalgamemanagers.assets |

---

## 💾 Profile System

Profiles let you maintain multiple background sets and switch between them without re-importing images each time.

- **Default (Original)** - locked, read-only. Always reflects the unmodified originals. Cannot be renamed or deleted.
- **New** - create a named profile and assign replacement images to any backgrounds you want.
- **Duplicate** - copy any profile as a starting point for a new one.
- **Rename / Delete** - available on any non-Default profile.

Profiles and the last-used folder path are saved automatically to `ch_bg_config.json` and `ch_bg_profiles.json` alongside the exe.

---

## 🔒 Backup System

On the first **Load & Scan** of any folder, the tool automatically copies the original asset files into a `_CH_BG_Backups` subfolder inside `Clone Hero_Data`. This happens once — subsequent scans skip files that are already backed up.

- The **Restore Backups** button (in the folder bar) copies all backed-up files back over the live game files and triggers a fresh scan.
- The backup status indicator in the folder bar shows whether backups are present for the current folder.
- **Apply & Save is blocked** if no backups exist, as a safety measure.

---

## 🐛 Troubleshooting

**Backgrounds show "No texture matched"**
Make sure you selected the `Clone Hero_Data` folder, not the game's root folder or a subfolder inside it.

**Changes are reverted after launching the game**
The Clone Hero launcher is resetting your files. See the important note at the top of this README.

**Export Original shows a very small or wrong image**
Some textures share similar names across multiple asset files. The tool pins `Logo_Transparent` strictly to `globalgamemanagers.assets` to avoid this, but if you see it on another background, open an issue.

**Image rejected as too small**
Your replacement image must meet the minimum resolution for that background. Upscale it to at least 1920x1080 (or exactly 2030x1328 for Logo_Transparent) before importing.

---

## 🔧 Running from Source

If you want to run the `.py` directly instead of using the exe:

```
pip install Pillow UnityPy
python clone_hero_bg_changer.py
```

Python 3.9 or newer required.

---

## 📄 License

MIT License - free to use, modify, and distribute.

---

## 🎮 Related Projects

- [Clone Hero](https://clonehero.net/) - The rhythm game this tool supports
- [CHColorGen](https://github.com/iamjrmh/CHColorGen) - Colored name generator for Clone Hero
- [Clone Hero Bad Songs Cleaner](https://github.com/iamjrmh/CloneHeroBadSongsCleaner) - Clean up problematic songs from your library
- [Chorus](https://chorus.fightthe.pw/) - Song database and downloader

---

Made with 🎸 by JURMR
