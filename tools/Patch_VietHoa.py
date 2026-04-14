"""
Patch_VietHoa.py — Installer ban Viet hoa Crimson Desert

GUI installer than thien voi user:
  - Tu dong tim duong dan game qua Steam Registry
  - Cho phep chon thu cong neu khong tim thay
  - One-click cai dat: copy mod files + patch 0.papgt
  - Hien thi trang thai ro rang

Cach dung:
  1. Dat file nay (hoac .exe) cung thu muc voi folder 0020/
  2. Chay file nay
  3. Nhan "Cai Dat Viet Hoa"
"""

import sys
import os
import struct
import shutil
import winreg
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading

PA_MAGIC = 0x2145E233


def rol(x, k):
    return ((x << k) & 0xFFFFFFFF) | (x >> (32 - k))


def ror(x, k):
    return (x >> k) | ((x << (32 - k)) & 0xFFFFFFFF)


def pa_checksum(data: bytes):
    length = len(data)
    if length == 0:
        return 0

    a = b = c = (length - PA_MAGIC) & 0xFFFFFFFF
    offset = 0
    remaining = length

    while remaining > 12:
        a = (a + struct.unpack_from("<I", data, offset)[0]) & 0xFFFFFFFF
        b = (b + struct.unpack_from("<I", data, offset + 4)[0]) & 0xFFFFFFFF
        c = (c + struct.unpack_from("<I", data, offset + 8)[0]) & 0xFFFFFFFF

        a = (a - c) & 0xFFFFFFFF; a ^= rol(c, 4); c = (c + b) & 0xFFFFFFFF
        b = (b - a) & 0xFFFFFFFF; b ^= rol(a, 6); a = (a + c) & 0xFFFFFFFF
        c = (c - b) & 0xFFFFFFFF; c ^= rol(b, 8); b = (b + a) & 0xFFFFFFFF
        a = (a - c) & 0xFFFFFFFF; a ^= rol(c, 16); c = (c + b) & 0xFFFFFFFF
        b = (b - a) & 0xFFFFFFFF; b ^= rol(a, 19); a = (a + c) & 0xFFFFFFFF
        c = (c - b) & 0xFFFFFFFF; c ^= rol(b, 4); b = (b + a) & 0xFFFFFFFF

        offset += 12
        remaining -= 12

    tail = data[offset:]

    for i in range(remaining):
        byte = tail[i]
        if i < 4:
            a = (a + (byte << (8 * i))) & 0xFFFFFFFF
        elif i < 8:
            b = (b + (byte << (8 * (i - 4)))) & 0xFFFFFFFF
        else:
            c = (c + (byte << (8 * (i - 8)))) & 0xFFFFFFFF

    v82 = ((b ^ c) - rol(b, 14)) & 0xFFFFFFFF
    v83 = ((a ^ v82) - rol(v82, 11)) & 0xFFFFFFFF
    v84 = ((v83 ^ b) - ror(v83, 7)) & 0xFFFFFFFF
    v85 = ((v84 ^ v82) - rol(v84, 16)) & 0xFFFFFFFF
    v86 = rol(v85, 4)
    t = ((v83 ^ v85) - v86) & 0xFFFFFFFF
    v87 = ((t ^ v84) - rol(t, 14)) & 0xFFFFFFFF

    return ((v87 ^ v85) - ror(v87, 8)) & 0xFFFFFFFF


def parse_papgt_entries(papgt: bytes):
    """Parse 0.papgt string table to build a map of folder_name -> entry CRC offset."""
    entry_count = papgt[8]
    entry_table_end = 12 + entry_count * 12
    str_table_start = entry_table_end + 4

    result = {}
    for i in range(entry_count):
        entry_off = 12 + i * 12
        str_off = struct.unpack_from("<I", papgt, entry_off + 4)[0]
        crc_offset = entry_off + 8

        name_start = str_table_start + str_off
        if name_start >= len(papgt):
            continue
        name_end = papgt.index(0, name_start) if 0 in papgt[name_start:name_start + 10] else name_start + 4
        folder_name = papgt[name_start:name_end].decode("ascii", errors="replace")

        result[folder_name] = crc_offset

    return result


# ─── Auto-detect game path ────────────────────────────────────────

def find_steam_libraries():
    """Find all Steam library folders from registry and libraryfolders.vdf."""
    libraries = []

    # Method 1: Read Steam install path from registry
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Valve\Steam")
        steam_path = Path(winreg.QueryValueEx(key, "SteamPath")[0])
        winreg.CloseKey(key)

        default_lib = steam_path / "steamapps" / "common"
        if default_lib.exists():
            libraries.append(default_lib)

        # Parse libraryfolders.vdf for additional libraries
        vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
        if vdf_path.exists():
            vdf_text = vdf_path.read_text(encoding="utf-8", errors="ignore")
            import re
            paths = re.findall(r'"path"\s+"([^"]+)"', vdf_text)
            for p in paths:
                lib = Path(p.replace("\\\\", "\\")) / "steamapps" / "common"
                if lib.exists() and lib not in libraries:
                    libraries.append(lib)
    except (OSError, FileNotFoundError):
        pass

    # Method 2: Check common default paths
    for drive in "CDEFGH":
        for steam_dir in [
            f"{drive}:\\Program Files (x86)\\Steam\\steamapps\\common",
            f"{drive}:\\Program Files\\Steam\\steamapps\\common",
            f"{drive}:\\Steam\\steamapps\\common",
            f"{drive}:\\SteamLibrary\\steamapps\\common",
        ]:
            p = Path(steam_dir)
            if p.exists() and p not in libraries:
                libraries.append(p)

    return libraries


def auto_detect_game_path():
    """Try to find Crimson Desert installation directory."""
    game_names = ["Crimson Desert", "CrimsonDesert"]

    for lib in find_steam_libraries():
        for name in game_names:
            game_dir = lib / name
            if game_dir.exists() and (game_dir / "meta" / "0.papgt").exists():
                return str(game_dir)

    return ""


def get_mod_source_dir():
    """Get the directory containing the mod files (next to this script/exe)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


# ─── Install logic ────────────────────────────────────────────────

def do_install(game_path: str, log_callback, progress_callback):
    """Perform the full installation: copy mod files + patch 0.papgt.

    Args:
        game_path: Path to game root directory
        log_callback: function(message: str) to log status
        progress_callback: function(value: int) to update progress (0-100)
    """
    game_root = Path(game_path)
    mod_source = get_mod_source_dir()

    # ── Validate paths ──────────────────────────────────────
    papgt_path = game_root / "meta" / "0.papgt"
    if not papgt_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy 'meta/0.papgt' trong:\n{game_root}\n\n"
            "Hãy chắc chắn bạn đã chọn đúng thư mục game Crimson Desert."
        )

    # Find mod folders next to this exe/script
    mod_folders = sorted([
        f for f in mod_source.iterdir()
        if f.is_dir() and f.name.isdigit() and (f / "0.pamt").exists()
    ])

    if not mod_folders:
        raise FileNotFoundError(
            f"Không tìm thấy thư mục mod (VD: 0020/) cạnh file cài đặt:\n{mod_source}\n\n"
            "Hãy chắc chắn folder mod nằm cùng thư mục với file .exe này."
        )

    progress_callback(10)

    # ── Step 1: Backup original game files ───────────────────
    log_callback("💾 Đang backup file gốc...")

    for i, folder in enumerate(mod_folders):
        folder_name = folder.name
        target = game_root / folder_name
        backup_dir = game_root / "meta" / "viethoa_backup" / folder_name

        if target.exists() and not backup_dir.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Backup original 0.pamt
            orig_pamt = target / "0.pamt"
            if orig_pamt.exists():
                shutil.copy2(orig_pamt, backup_dir / "0.pamt")
                log_callback(f"   ✓ Backup {folder_name}/0.pamt")

            # Backup original .paz files
            for paz in target.glob("*.paz"):
                shutil.copy2(paz, backup_dir / paz.name)
                log_callback(f"   ✓ Backup {folder_name}/{paz.name}")
        else:
            log_callback(f"   ✓ Backup {folder_name} đã tồn tại")

    progress_callback(20)

    # ── Step 2: Copy mod files to game ──────────────────────
    log_callback("\n📂 Đang copy file mod vào thư mục game...")

    for i, folder in enumerate(mod_folders):
        folder_name = folder.name
        target = game_root / folder_name
        target.mkdir(exist_ok=True)

        # Copy 0.pamt
        src_pamt = folder / "0.pamt"
        if src_pamt.exists():
            shutil.copy2(src_pamt, target / "0.pamt")
            log_callback(f"   ✓ Đã copy {folder_name}/0.pamt")

        # Copy all .paz files
        for paz in folder.glob("*.paz"):
            log_callback(f"   ✓ Đang copy {folder_name}/{paz.name}...")
            shutil.copy2(paz, target / paz.name)

        progress_callback(20 + int(40 * (i + 1) / len(mod_folders)))

    # ── Step 3: Backup 0.papgt ──────────────────────────────
    log_callback("\n💾 Đang backup meta/0.papgt...")
    papgt_backup = game_root / "meta" / "viethoa_backup" / "0.papgt"
    papgt_backup.parent.mkdir(parents=True, exist_ok=True)
    if not papgt_backup.exists():
        shutil.copy2(papgt_path, papgt_backup)
        log_callback("   ✓ Đã tạo backup: 0.papgt")
    else:
        log_callback("   ✓ Backup đã tồn tại")

    progress_callback(65)

    # ── Step 4: Patch 0.papgt ───────────────────────────────
    log_callback("\n🔧 Đang cập nhật CheckSum trong 0.papgt...")

    with open(papgt_path, "rb") as f:
        papgt = bytearray(f.read())

    entry_map = parse_papgt_entries(papgt)
    changed = False

    for folder in mod_folders:
        folder_name = folder.name

        if folder_name not in entry_map:
            log_callback(f"   ⚠ Thư mục {folder_name} không có trong 0.papgt, bỏ qua")
            continue

        crc_offset = entry_map[folder_name]

        # Read the PAMT from the game directory (after copy)
        pamt_path = game_root / folder_name / "0.pamt"
        with open(pamt_path, "rb") as f:
            pamt = f.read()

        real_crc = pa_checksum(pamt[12:])
        old_crc = struct.unpack_from("<I", papgt, crc_offset)[0]

        if old_crc == real_crc:
            log_callback(f"   ✓ {folder_name}: CRC đã đúng")
        else:
            struct.pack_into("<I", papgt, crc_offset, real_crc)
            log_callback(f"   ✓ {folder_name}: 0x{old_crc:08X} → 0x{real_crc:08X}")
            changed = True

    progress_callback(85)

    # ── Step 5: Save patched 0.papgt ────────────────────────
    if changed:
        papgt_hash = pa_checksum(papgt[12:])
        struct.pack_into("<I", papgt, 4, papgt_hash)

        with open(papgt_path, "wb") as f:
            f.write(papgt)
        log_callback(f"\n   ✓ Đã lưu 0.papgt (hash: 0x{papgt_hash:08X})")
    else:
        log_callback("\n   ✓ 0.papgt không cần thay đổi")

    progress_callback(100)
    log_callback("\n" + "=" * 45)
    log_callback("✅ CÀI ĐẶT VIỆT HÓA THÀNH CÔNG!")
    log_callback("=" * 45)
    log_callback("\nBạn có thể vào game ngay bây giờ.")
    log_callback("Để gỡ cài đặt, nhấn nút 'GỠ VIỆT HÓA' trên giao diện.")
    log_callback("Nếu game cập nhật, chạy lại tool này là được.")


def do_uninstall(game_path: str, log_callback, progress_callback):
    """Restore original game files from backup, then recalculate 0.papgt CRC.

    This function must be called from the MAIN THREAD with direct (non-threaded)
    log_callback and progress_callback, since uninstall is fast enough.
    """
    game_root = Path(game_path)
    backup_root = game_root / "meta" / "viethoa_backup"

    if not backup_root.exists():
        raise FileNotFoundError(
            "Không tìm thấy thư mục backup.\n\n"
            "Có thể bạn chưa từng cài Việt Hóa bằng tool này,\n"
            "hoặc backup đã bị xóa.\n\n"
            "Để khôi phục, hãy Verify game files qua Steam."
        )

    progress_callback(10)

    # ── Step 1: Restore mod folder files ────────────────────
    log_callback("🔄 Đang khôi phục file gốc...")

    backup_folders = sorted([
        f for f in backup_root.iterdir()
        if f.is_dir() and f.name.isdigit()
    ])

    restored_folders = []

    for i, bak_folder in enumerate(backup_folders):
        folder_name = bak_folder.name
        target = game_root / folder_name

        if not target.exists():
            log_callback(f"   ⚠ Thư mục {folder_name} không tồn tại, bỏ qua")
            continue

        # Restore 0.pamt — show size comparison for verification
        bak_pamt = bak_folder / "0.pamt"
        if bak_pamt.exists():
            cur_pamt = target / "0.pamt"
            bak_size = bak_pamt.stat().st_size
            cur_size = cur_pamt.stat().st_size if cur_pamt.exists() else 0
            shutil.copy2(bak_pamt, cur_pamt)
            log_callback(f"   ✓ Khôi phục {folder_name}/0.pamt ({cur_size}B → {bak_size}B)")

        # Restore .paz files
        for paz in bak_folder.glob("*.paz"):
            cur_paz = target / paz.name
            bak_size = paz.stat().st_size
            cur_size = cur_paz.stat().st_size if cur_paz.exists() else 0
            shutil.copy2(paz, cur_paz)
            log_callback(f"   ✓ Khôi phục {folder_name}/{paz.name} ({cur_size:,}B → {bak_size:,}B)")

        restored_folders.append(folder_name)
        progress_callback(10 + int(40 * (i + 1) / max(len(backup_folders), 1)))

    # ── Step 2: Restore ORIGINAL 0.papgt + recalculate CRC ────
    papgt_path = game_root / "meta" / "0.papgt"
    papgt_backup = backup_root / "0.papgt"

    # First: restore the original 0.papgt if we have a backup
    if papgt_backup.exists():
        log_callback("\n🔄 Khôi phục 0.papgt gốc từ backup...")
        shutil.copy2(papgt_backup, papgt_path)
        log_callback("   ✓ Đã khôi phục 0.papgt")

    # Then: verify CRC matches the restored 0.pamt files
    log_callback("\n🔧 Đang xác minh CheckSum trong 0.papgt...")

    with open(papgt_path, "rb") as f:
        papgt = bytearray(f.read())

    entry_map = parse_papgt_entries(papgt)
    changed = False

    for folder_name in restored_folders:
        if folder_name not in entry_map:
            log_callback(f"   ⚠ {folder_name} không có trong 0.papgt, bỏ qua")
            continue

        crc_offset = entry_map[folder_name]
        pamt_path = game_root / folder_name / "0.pamt"

        with open(pamt_path, "rb") as f:
            pamt = f.read()

        real_crc = pa_checksum(pamt[12:])
        old_crc = struct.unpack_from("<I", papgt, crc_offset)[0]

        if old_crc != real_crc:
            struct.pack_into("<I", papgt, crc_offset, real_crc)
            log_callback(f"   ✓ {folder_name}: 0x{old_crc:08X} → 0x{real_crc:08X}")
            changed = True
        else:
            log_callback(f"   ✓ {folder_name}: CRC khớp ✅")

    if changed:
        papgt_hash = pa_checksum(papgt[12:])
        struct.pack_into("<I", papgt, 4, papgt_hash)
        with open(papgt_path, "wb") as f:
            f.write(papgt)
        log_callback(f"   ✓ Đã lưu 0.papgt (hash: 0x{papgt_hash:08X})")
    else:
        log_callback("   ✓ 0.papgt CRC đã đúng, không cần sửa")

    progress_callback(80)

    # ── Step 3: Clean up backup folder ──────────────────────
    log_callback("\n🧹 Đang dọn dẹp backup...")
    shutil.rmtree(backup_root)
    log_callback("   ✓ Đã xóa thư mục backup")

    progress_callback(100)
    log_callback("\n" + "=" * 45)
    log_callback("✅ GỠ CÀI ĐẶT THÀNH CÔNG!")
    log_callback("=" * 45)
    log_callback("\nGame đã được khôi phục về trạng thái gốc.")


# ─── GUI ──────────────────────────────────────────────────────────

class InstallerApp:
    # Color scheme
    BG = "#1a1a2e"
    BG_LIGHT = "#16213e"
    ACCENT = "#e94560"
    ACCENT_HOVER = "#ff6b81"
    TEXT = "#eaeaea"
    TEXT_DIM = "#8899aa"
    SUCCESS = "#2ecc71"
    ENTRY_BG = "#0f3460"
    ENTRY_FG = "#eaeaea"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cài Đặt Việt Hóa — Crimson Desert")
        self.root.geometry("620x520")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)

        # Center window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 620) // 2
        y = (self.root.winfo_screenheight() - 520) // 2
        self.root.geometry(f"620x520+{x}+{y}")

        # Try to set icon (optional)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self._build_ui()
        self._auto_detect()

    def _build_ui(self):
        # ── Title ───────────────────────────────────────────
        title_frame = tk.Frame(self.root, bg=self.BG)
        title_frame.pack(fill="x", padx=20, pady=(15, 0))

        title = tk.Label(
            title_frame,
            text="🎮  CÀI ĐẶT VIỆT HÓA",
            font=("Segoe UI", 18, "bold"),
            fg=self.TEXT, bg=self.BG
        )
        title.pack()

        subtitle = tk.Label(
            title_frame,
            text="CRIMSON DESERT",
            font=("Segoe UI", 12),
            fg=self.ACCENT, bg=self.BG
        )
        subtitle.pack()

        # ── Separator ──────────────────────────────────────
        sep = tk.Frame(self.root, bg=self.ACCENT, height=2)
        sep.pack(fill="x", padx=20, pady=(10, 15))

        # ── Game path selector ─────────────────────────────
        path_frame = tk.Frame(self.root, bg=self.BG)
        path_frame.pack(fill="x", padx=20)

        path_label = tk.Label(
            path_frame,
            text="📁  Thư mục game Crimson Desert:",
            font=("Segoe UI", 10),
            fg=self.TEXT, bg=self.BG,
            anchor="w"
        )
        path_label.pack(fill="x")

        entry_frame = tk.Frame(path_frame, bg=self.BG)
        entry_frame.pack(fill="x", pady=(5, 0))

        self.path_var = tk.StringVar()
        self.path_entry = tk.Entry(
            entry_frame,
            textvariable=self.path_var,
            font=("Segoe UI", 10),
            bg=self.ENTRY_BG, fg=self.ENTRY_FG,
            insertbackground=self.TEXT,
            relief="flat",
            bd=0
        )
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

        browse_btn = tk.Button(
            entry_frame,
            text="Chọn...",
            font=("Segoe UI", 9),
            bg=self.BG_LIGHT, fg=self.TEXT,
            activebackground=self.ACCENT,
            activeforeground="white",
            relief="flat", bd=0,
            cursor="hand2",
            command=self._browse
        )
        browse_btn.pack(side="right", ipady=4, ipadx=10)

        # ── Status label ───────────────────────────────────
        self.status_label = tk.Label(
            self.root,
            text="",
            font=("Segoe UI", 9),
            fg=self.TEXT_DIM, bg=self.BG,
            anchor="w"
        )
        self.status_label.pack(fill="x", padx=20, pady=(5, 0))

        # ── Log area ───────────────────────────────────────
        log_frame = tk.Frame(self.root, bg=self.BG)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        self.log_text = tk.Text(
            log_frame,
            font=("Consolas", 9),
            bg=self.BG_LIGHT, fg=self.TEXT,
            relief="flat", bd=0,
            wrap="word",
            state="disabled",
            height=12
        )
        self.log_text.pack(fill="both", expand=True)

        # Configure text tags for colored output
        self.log_text.tag_configure("success", foreground=self.SUCCESS)
        self.log_text.tag_configure("error", foreground=self.ACCENT)
        self.log_text.tag_configure("info", foreground=self.TEXT_DIM)

        # ── Progress bar ───────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=self.BG_LIGHT,
            background=self.ACCENT,
            lightcolor=self.ACCENT,
            darkcolor=self.ACCENT,
            bordercolor=self.BG_LIGHT,
            thickness=6
        )

        self.progress = ttk.Progressbar(
            self.root,
            style="Custom.Horizontal.TProgressbar",
            orient="horizontal",
            length=100,
            mode="determinate"
        )
        self.progress.pack(fill="x", padx=20, pady=(8, 0))

        # ── Buttons ─────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=self.BG)
        btn_frame.pack(fill="x", padx=20, pady=(12, 0))

        self.install_btn = tk.Button(
            btn_frame,
            text="⚡  CÀI ĐẶT VIỆT HÓA",
            font=("Segoe UI", 12, "bold"),
            bg=self.ACCENT, fg="white",
            activebackground=self.ACCENT_HOVER,
            activeforeground="white",
            relief="flat", bd=0,
            cursor="hand2",
            command=self._install
        )
        self.install_btn.pack(fill="x", ipady=8)

        # Hover effects for install button
        self.install_btn.bind("<Enter>", lambda e: self.install_btn.configure(bg=self.ACCENT_HOVER))
        self.install_btn.bind("<Leave>", lambda e: self.install_btn.configure(bg=self.ACCENT))

        # Uninstall button
        self.uninstall_btn = tk.Button(
            btn_frame,
            text="🗑  GỠ VIỆT HÓA",
            font=("Segoe UI", 9),
            bg=self.BG_LIGHT, fg=self.TEXT_DIM,
            activebackground="#c0392b",
            activeforeground="white",
            relief="flat", bd=0,
            cursor="hand2",
            command=self._uninstall
        )
        self.uninstall_btn.pack(fill="x", ipady=4, pady=(6, 0))

        # Hover effects for uninstall button
        self.uninstall_btn.bind("<Enter>", lambda e: self.uninstall_btn.configure(bg="#c0392b", fg="white"))
        self.uninstall_btn.bind("<Leave>", lambda e: self.uninstall_btn.configure(bg=self.BG_LIGHT, fg=self.TEXT_DIM))

        # ── Credit ─────────────────────────────────────────
        credit = tk.Label(
            self.root,
            text="Crimson Desert Localization Tool | newone9852 (translator)",
            font=("Segoe UI", 8),
            fg=self.TEXT_DIM, bg=self.BG
        )
        credit.pack(pady=(6, 8))

    def _auto_detect(self):
        """Try to auto-detect game path on startup."""
        self.status_label.configure(text="🔍 Đang tìm thư mục game...", fg=self.TEXT_DIM)
        self.root.update()

        detected = auto_detect_game_path()
        if detected:
            self.path_var.set(detected)
            self.status_label.configure(
                text=f"✓ Đã tìm thấy game tự động",
                fg=self.SUCCESS
            )
        else:
            self.status_label.configure(
                text="⚠ Không tìm thấy game tự động. Hãy chọn thư mục game.",
                fg="#f39c12"
            )

        # Check mod files
        mod_source = get_mod_source_dir()
        mod_folders = [
            f for f in mod_source.iterdir()
            if f.is_dir() and f.name.isdigit() and (f / "0.pamt").exists()
        ]
        if mod_folders:
            self._log(f"📦 File mod: {', '.join(f.name for f in mod_folders)}\n", "info")
        else:
            self._log("⚠ Không tìm thấy file mod cạnh file .exe này!\n", "error")

    def _browse(self):
        """Open folder picker for game directory."""
        path = filedialog.askdirectory(
            title="Chọn thư mục game Crimson Desert",
            initialdir=self.path_var.get() or "C:\\"
        )
        if path:
            self.path_var.set(path)
            # Validate
            if (Path(path) / "meta" / "0.papgt").exists():
                self.status_label.configure(
                    text="✓ Thư mục game hợp lệ",
                    fg=self.SUCCESS
                )
            else:
                self.status_label.configure(
                    text="⚠ Không tìm thấy meta/0.papgt trong thư mục này",
                    fg="#f39c12"
                )

    def _log(self, message, tag=None):
        """Thread-safe: append message to log area via root.after()."""
        def _do():
            self.log_text.configure(state="normal")
            if tag:
                self.log_text.insert("end", message + "\n", tag)
            else:
                self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(0, _do)

    def _log_direct(self, message, tag=None):
        """Direct UI update (main thread only). For synchronous operations."""
        self.log_text.configure(state="normal")
        if tag:
            self.log_text.insert("end", message + "\n", tag)
        else:
            self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.root.update_idletasks()

    def _set_progress(self, value):
        """Thread-safe: update progress bar via root.after()."""
        self.root.after(0, lambda: self.progress.configure(value=value))

    def _set_progress_direct(self, value):
        """Direct progress update (main thread only)."""
        self.progress.configure(value=value)
        self.root.update_idletasks()

    def _install(self):
        """Run installation in main thread (with UI updates)."""
        game_path = self.path_var.get().strip()

        if not game_path:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng chọn thư mục game Crimson Desert."
            )
            return

        if not (Path(game_path) / "meta" / "0.papgt").exists():
            messagebox.showerror(
                "Thư mục không hợp lệ",
                f"Không tìm thấy 'meta/0.papgt' trong:\n{game_path}\n\n"
                "Hãy chắc chắn bạn đã chọn đúng thư mục game."
            )
            return

        # Clear log
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        # Disable button during install
        self.install_btn.configure(state="disabled", text="⏳  ĐANG CÀI ĐẶT...", bg=self.TEXT_DIM)

        def run():
            try:
                do_install(game_path, self._log, self._set_progress)
                self.root.after(0, self._on_success)
            except Exception as e:
                self.root.after(0, lambda: self._on_error(str(e)))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        # Poll thread completion
        def check():
            if thread.is_alive():
                self.root.after(100, check)
            # Thread finished, button re-enabled in _on_success or _on_error
        self.root.after(100, check)

    def _uninstall(self):
        """Run uninstallation SYNCHRONOUSLY on the main thread.

        Unlike install (which copies large files), uninstall is fast enough
        to run on the main thread without freezing the UI.
        This avoids all threading/deadlock issues.
        """
        game_path = self.path_var.get().strip()

        if not game_path:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng chọn thư mục game Crimson Desert."
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận gỡ cài đặt",
            "Bạn có chắc muốn gỡ Việt Hóa?\n\n"
            "Game sẽ được khôi phục về ngôn ngữ gốc."
        )
        if not confirm:
            return

        # Clear log
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        self.uninstall_btn.configure(state="disabled", text="⏳  ĐANG GỠ...", bg=self.TEXT_DIM)
        self.install_btn.configure(state="disabled")
        self.root.update_idletasks()

        # Run synchronously on main thread (no threading issues)
        try:
            do_uninstall(game_path, self._log_direct, self._set_progress_direct)
            self._on_uninstall_success()
        except Exception as e:
            self._on_error(str(e))

    def _on_success(self):
        """Called when installation succeeds."""
        self.install_btn.configure(
            state="normal",
            text="✅  CÀI ĐẶT THÀNH CÔNG!",
            bg=self.SUCCESS
        )
        self.uninstall_btn.configure(state="normal")
        self.status_label.configure(
            text="✅ Cài đặt Việt Hóa thành công! Bạn có thể vào game ngay.",
            fg=self.SUCCESS
        )
        # Reset button after 3 seconds
        self.root.after(3000, lambda: self.install_btn.configure(
            text="⚡  CÀI ĐẶT VIỆT HÓA",
            bg=self.ACCENT
        ))

    def _on_uninstall_success(self):
        """Called when uninstallation succeeds."""
        self.uninstall_btn.configure(
            state="normal",
            text="✅  ĐÃ GỠ XONG!",
            bg=self.SUCCESS,
            fg="white"
        )
        self.install_btn.configure(state="normal")
        self.status_label.configure(
            text="✅ Đã gỡ Việt Hóa. Game đã trở về ngôn ngữ gốc.",
            fg=self.SUCCESS
        )
        self.root.after(3000, lambda: self.uninstall_btn.configure(
            text="🗑  GỠ VIỆT HÓA",
            bg=self.BG_LIGHT,
            fg=self.TEXT_DIM
        ))

    def _on_error(self, error_msg):
        """Called when an operation fails."""
        self._log(f"\n❌ LỖI: {error_msg}", "error")
        self.install_btn.configure(
            state="normal",
            text="⚡  CÀI ĐẶT VIỆT HÓA",
            bg=self.ACCENT
        )
        self.uninstall_btn.configure(
            state="normal",
            text="🗑  GỠ VIỆT HÓA",
            bg=self.BG_LIGHT,
            fg=self.TEXT_DIM
        )
        self.status_label.configure(
            text="❌ Thao tác thất bại. Xem chi tiết bên dưới.",
            fg=self.ACCENT
        )
        messagebox.showerror(
            "Lỗi",
            f"Có lỗi xảy ra:\n\n{error_msg}"
        )

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = InstallerApp()
    app.run()
