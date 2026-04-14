# Crimson Desert Vietnamese Localization Tool

A Python-based tool for managing Vietnamese localization for **Crimson Desert**. It handles unpacking/repacking PALOC/PAZ game files and includes a standalone installer (`Patch_VietHoa.exe`) for easy one-click installation.

**Mod page**: [Nexus Mods](https://www.nexusmods.com/crimsondesert/mods/342)

---

## Repository Structure

```
├── Crimson_Desert_Localization_Tool.py   # Main GUI tool (PyQt6) — for mod developers
├── tools/
│   ├── Patch_VietHoa.py                  # Standalone installer GUI (tkinter) — for end users
│   ├── paz_unpack.py                     # PAZ archive unpacker
│   ├── paz_repack.py                     # PAZ archive repacker
│   ├── paz_crypto.py                     # PAZ encryption/decryption
│   ├── paz_parse.py                      # PAZ format parser
│   ├── paloc_Tool.py                     # PALOC export/import tool
│   ├── Meta_Patch.py                     # 0.papgt metadata patcher
│   └── version_info.txt                  # Windows version resource for exe
├── requirements.txt                      # Python dependencies
└── install_requirements.bat              # Quick dependency installer
```

## What does `Patch_VietHoa.exe` do?

`Patch_VietHoa.exe` is the compiled version of `tools/Patch_VietHoa.py`. It is a **standalone, offline installer** that:

1. Auto-detects the Crimson Desert game directory via Steam Registry
2. Copies Vietnamese localization files (`.pamt`, `.paz`) to the game folder
3. Recalculates CRC checksums in `meta/0.papgt` so the game accepts the modified files
4. Provides one-click uninstall to restore original game files from backup

It has **no internet connectivity**, **no telemetry**, and only modifies game files in the user's local game directory.

---

## Build Instructions

### Prerequisites

- **Python**: 3.10 or higher ([python.org](https://www.python.org/downloads/))
- **OS**: Windows 10/11 (the installer uses `winreg` for Steam detection and `tkinter` for GUI)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Build with PyInstaller

```bash
pip install pyinstaller

cd tools
pyinstaller --onefile --noconsole --version-file=version_info.txt Patch_VietHoa.py
```

The output executable will be at: `tools/dist/Patch_VietHoa.exe`

### Alternative: Build with Nuitka

```bash
pip install nuitka

cd tools
python -m nuitka --onefile --windows-console-mode=disable Patch_VietHoa.py
```

The output executable will be at: `tools/Patch_VietHoa.exe`

### Step 3: Verify Build

After building, you can compare the checksum of your built executable against the one uploaded to Nexus Mods:

```powershell
# PowerShell
Get-FileHash .\dist\Patch_VietHoa.exe -Algorithm SHA256
```

---

## Development Setup (for the main Localization Tool)

The main tool (`Crimson_Desert_Localization_Tool.py`) is a PyQt6 GUI used during mod development. It is **not** included in the Nexus Mods release — only `Patch_VietHoa.exe` and the language data files are distributed to end users.

```bash
pip install -r requirements.txt
python Crimson_Desert_Localization_Tool.py
```

---

## License

This tool is provided for the Crimson Desert modding community. Do not use it to sell mods.

## Author

**newone9852** — Translator & Tool Developer
