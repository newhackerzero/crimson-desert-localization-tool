import sys
import json
import shutil
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QTabWidget, QTextEdit,
    QProgressBar, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt

BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "tools"
CONFIG_FILE = BASE_DIR / "config.json"

LANGUAGE_MAP = {
    "English": ("0020", "localizationstring_eng.paloc", "basefont_eng.ttf"),
    "Korean": ("0019", "localizationstring_kor.paloc", "basefont_kor.ttf"),
    "Japanese": ("0021", "localizationstring_jpn.paloc", "basefont_jpn.ttf"),
    "Russian": ("0022", "localizationstring_rus.paloc", "basefont_rus.ttf"),
    "Turkish": ("0023", "localizationstring_tur.paloc", "basefont_tur.ttf"),
    "Spanish": ("0024", "localizationstring_spa-es.paloc", "basefont_spa-es.ttf"),
    "Mexican Spanish": ("0025", "localizationstring_spa-mx.paloc", "basefont_spa-mx.ttf"),
    "French": ("0026", "localizationstring_fre.paloc", "basefont_fre.ttf"),
    "German": ("0027", "localizationstring_ger.paloc", "basefont_ger.ttf"),
    "Italian": ("0028", "localizationstring_ita.paloc", "basefont_ita.ttf"),
    "Polish": ("0029", "localizationstring_pol.paloc", "basefont_pol.ttf"),
    "Portuguese - Brazil": ("0030", "localizationstring_por-br.paloc", "basefont_por-br.ttf"),
    "Traditional Chinese": ("0031", "localizationstring_zho-tw.paloc", "basefont_zho-tw.ttf"),
    "Simplified Chinese": ("0032", "localizationstring_zho-cn.paloc", "basefont_zho-cn.ttf"),
}


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

    return {
        "game_path": "",
        "language": "",
        "first_run": True,
        "release_copy": True
    }


def save_config(data):
    CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


CONFIG = load_config()


def run_command(cmd, cwd=None):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or BASE_DIR
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def get_localization_folder():
    return LANGUAGE_MAP[CONFIG["language"]][0]


def get_paloc_entry():
    return f"gamedata/{LANGUAGE_MAP[CONFIG['language']][1]}"


def get_language_font():
    return LANGUAGE_MAP[CONFIG["language"]][2]


def _copy_patcher_to_release(release_root):
    """Copy Patch_VietHoa (.exe or .py) to the release folder.

    Instead of shipping a full 0.papgt (which breaks on game updates and
    conflicts with CD JSON Mod Manager), we ship the patcher so users
    can update their own 0.papgt safely.
    """
    patcher_exe = TOOLS_DIR / "dist" / "Patch_VietHoa.exe"
    patcher_py = TOOLS_DIR / "Patch_VietHoa.py"

    if patcher_exe.exists():
        shutil.copy2(patcher_exe, release_root / "Patch_VietHoa.exe")
    elif patcher_py.exists():
        shutil.copy2(patcher_py, release_root / "Patch_VietHoa.py")


def copy_localization_to_release(folder):
    if not CONFIG.get("release_copy", True):
        return

    release_root = BASE_DIR / "Mod files for release"
    release_root.mkdir(exist_ok=True)

    target = release_root / folder.name
    target.mkdir(exist_ok=True)

    # copy 0.pamt
    pamt = folder / "0.pamt"
    if pamt.exists():
        shutil.copy2(pamt, target / "0.pamt")

    # copy all paz
    for paz in folder.glob("*.paz"):
        shutil.copy2(paz, target / paz.name)

    # Copy patcher instead of 0.papgt (avoids game update & mod manager conflicts)
    _copy_patcher_to_release(release_root)


def copy_fonts_to_release(folder):
    if not CONFIG.get("release_copy", True):
        return

    release_root = BASE_DIR / "Mod files for release"
    release_root.mkdir(exist_ok=True)

    target = release_root / folder.name
    target.mkdir(exist_ok=True)

    # copy 0.pamt
    pamt = folder / "0.pamt"
    if pamt.exists():
        shutil.copy2(pamt, target / "0.pamt")

    # copy only last paz
    paz_files = sorted(folder.glob("*.paz"))
    if paz_files:
        last_paz = paz_files[-1]
        shutil.copy2(last_paz, target / last_paz.name)

    # Copy patcher instead of 0.papgt (avoids game update & mod manager conflicts)
    _copy_patcher_to_release(release_root)


class ToolPage(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(6)

    def add_path_selector(self, title, file_mode=False, filter_str="All Files (*)"):
        label = QLabel(title)
        line = QLineEdit()
        btn = QPushButton("Browse")

        def browse():
            if file_mode:
                path, _ = QFileDialog.getOpenFileName(self, title, "", filter_str)
            else:
                path = QFileDialog.getExistingDirectory(self, title)
            if path:
                line.setText(path)

        btn.clicked.connect(browse)

        row = QHBoxLayout()
        row.addWidget(label)
        row.addWidget(line)
        row.addWidget(btn)

        self.layout.addLayout(row)
        return line

    def add_progress(self):
        bar = QProgressBar()
        bar.setValue(0)
        self.layout.addWidget(bar)
        return bar

    def add_status(self):
        status = QTextEdit()
        status.setReadOnly(True)
        status.setFixedHeight(140)
        status.setText("Ready")
        self.layout.addWidget(status)
        return status


class SettingsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        folder_row = QHBoxLayout()

        folder_label = QLabel("Game Folder")
        folder_label.setFixedWidth(70)

        self.path_edit = QLineEdit(CONFIG["game_path"])

        browse = QPushButton("Browse")
        browse.setFixedWidth(80)

        def browse_folder():
            path = QFileDialog.getExistingDirectory(self, "Select Game Folder")
            if path:
                self.path_edit.setText(path)

        browse.clicked.connect(browse_folder)

        folder_row.addWidget(folder_label)
        folder_row.addWidget(self.path_edit)
        folder_row.addWidget(browse)

        layout.addLayout(folder_row)

        lang_row = QHBoxLayout()

        lang_label = QLabel("Language")
        lang_label.setFixedWidth(70)

        self.lang = QComboBox()
        self.lang.addItems(list(LANGUAGE_MAP.keys()))
        self.lang.setFixedWidth(220)

        if CONFIG["language"]:
            self.lang.setCurrentText(CONFIG["language"])
        else:
            self.lang.setCurrentIndex(-1)

        lang_row.addWidget(lang_label)
        lang_row.addWidget(self.lang)
        lang_row.addStretch()

        layout.addLayout(lang_row)

        self.release_checkbox = QCheckBox("Enable Mod files for release")
        self.release_checkbox.setChecked(CONFIG.get("release_copy", True))

        layout.addWidget(self.release_checkbox)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save)

        layout.addWidget(save_btn)
        layout.addStretch()

    def save(self):
        CONFIG["game_path"] = self.path_edit.text()
        CONFIG["language"] = self.lang.currentText()
        CONFIG["first_run"] = False
        CONFIG["release_copy"] = self.release_checkbox.isChecked()

        save_config(CONFIG)

        self.main_window.open_main_tabs()


class LocalizationPage(ToolPage):
    def __init__(self):
        super().__init__()

        self.paloc = self.add_path_selector("PALOC for Repack", file_mode=True, filter_str="PALOC Files (*.paloc)")

        btn_row = QHBoxLayout()
        unpack_btn = QPushButton("Unpack")
        repack_btn = QPushButton("Repack")

        unpack_btn.clicked.connect(self.unpack)
        repack_btn.clicked.connect(self.repack)

        btn_row.addWidget(unpack_btn)
        btn_row.addWidget(repack_btn)

        self.layout.addLayout(btn_row)

        self.progress = self.add_progress()
        self.status = self.add_status()

    def unpack(self):
        folder = Path(CONFIG["game_path"]) / get_localization_folder()
        out_dir = BASE_DIR / "Localization file"
        out_dir.mkdir(exist_ok=True)

        self.progress.setValue(25)

        ok, _ = run_command([
            sys.executable, str(TOOLS_DIR / "paz_unpack.py"),
            str(folder / "0.pamt"),
            "--paz-dir", str(folder)
        ], cwd=out_dir)

        self.progress.setValue(100 if ok else 0)

        self.status.setText(
            f"Unpack {'Success' if ok else 'Failed'}\nOutput: {out_dir}\nProgress: {self.progress.value()}%"
        )

    def repack(self):
        folder = Path(CONFIG["game_path"]) / get_localization_folder()

        self.progress.setValue(30)

        ok, _ = run_command([
            sys.executable, str(TOOLS_DIR / "paz_repack.py"),
            self.paloc.text(),
            "--pamt", str(folder / "0.pamt"),
            "--paz-dir", str(folder),
            "--entry", get_paloc_entry()
        ])

        if ok:
            self.progress.setValue(75)
            run_command([sys.executable, str(TOOLS_DIR / "Meta_Patch.py"), str(folder)])
            copy_localization_to_release(folder)
            self.progress.setValue(100)

        self.status.setText(
            f"Repack {'Success' if ok else 'Failed'}\nTarget: {folder}\nMeta Patch: {'Done' if ok else 'Skipped'}\nProgress: {self.progress.value()}%"
        )


class FontsPage(ToolPage):
    def __init__(self):
        super().__init__()

        self.fonts = self.add_path_selector("Fonts Folder (Repack)")

        btn_row = QHBoxLayout()
        unpack_btn = QPushButton("Unpack Fonts")
        repack_btn = QPushButton("Repack Fonts")

        unpack_btn.clicked.connect(self.unpack_fonts)
        repack_btn.clicked.connect(self.repack_fonts)

        btn_row.addWidget(unpack_btn)
        btn_row.addWidget(repack_btn)

        self.layout.addLayout(btn_row)

        self.progress = self.add_progress()
        self.status = self.add_status()

    def find_font_file(self, root, filename):
        for path in Path(root).rglob(filename):
            return path
        return None

    def unpack_fonts(self):
        folder = Path(CONFIG["game_path"]) / "0012"
        out_dir = BASE_DIR / "Fonts"
        out_dir.mkdir(exist_ok=True)

        targets = ["ui/creditfont.ttf", "ui/basefont.ttf", f"ui/{get_language_font()}"]

        ok = True

        for i, target in enumerate(targets, start=1):
            self.progress.setValue(i * 30)

            success, _ = run_command([
                sys.executable, str(TOOLS_DIR / "paz_unpack.py"),
                str(folder / "0.pamt"),
                "--paz-dir", str(folder),
                "--filter", target
            ], cwd=out_dir)

            if not success:
                ok = False

        self.progress.setValue(100 if ok else 0)

        self.status.setText(
            f"Unpack Fonts {'Success' if ok else 'Failed'}\nOutput: {out_dir}\nProgress: {self.progress.value()}%"
        )

    def repack_fonts(self):
        folder = Path(CONFIG["game_path"]) / "0012"
        font_dir = Path(self.fonts.text())

        files = [
            ("basefont.ttf", "ui/basefont.ttf"),
            (get_language_font(), f"ui/{get_language_font()}"),
            ("creditfont.ttf", "ui/creditfont.ttf")
        ]

        ok = True

        for i, (file_name, entry) in enumerate(files, start=1):
            self.progress.setValue(i * 25)

            font_path = self.find_font_file(font_dir, file_name)
            if not font_path:
                ok = False
                continue

            success, _ = run_command([
                sys.executable, str(TOOLS_DIR / "paz_repack.py"),
                str(font_path),
                "--pamt", str(folder / "0.pamt"),
                "--paz-dir", str(folder),
                "--entry", entry,
                "--append-last"
            ])

            if not success:
                ok = False

        if ok:
            run_command([sys.executable, str(TOOLS_DIR / "Meta_Patch.py"), str(folder)])
            copy_fonts_to_release(folder)
            self.progress.setValue(100)

        self.status.setText(
            f"Repack Fonts {'Success' if ok else 'Failed'}\nTarget: {folder}\nMeta Patch: {'Done' if ok else 'Skipped'}\nProgress: {self.progress.value()}%"
        )


class PalocPage(ToolPage):
    def __init__(self):
        super().__init__()

        self.paloc = self.add_path_selector("Export PALOC", file_mode=True, filter_str="PALOC Files (*.paloc)")
        self.json = self.add_path_selector("Import PALOC", file_mode=True, filter_str="JSON Files (*.json)")

        btn_row = QHBoxLayout()

        export_btn = QPushButton("Export")
        import_btn = QPushButton("Import")

        export_btn.clicked.connect(self.export_paloc)
        import_btn.clicked.connect(self.import_paloc)

        btn_row.addWidget(export_btn)
        btn_row.addWidget(import_btn)

        self.layout.addLayout(btn_row)

        self.progress = self.add_progress()
        self.status = self.add_status()

    def export_paloc(self):
        out_dir = BASE_DIR / "PALOC_Export"
        out_dir.mkdir(exist_ok=True)

        ok, log = run_command(
            [sys.executable, str(TOOLS_DIR / "paloc_Tool.py"), self.paloc.text()],
            cwd=out_dir
        )

        self.progress.setValue(100 if ok else 0)
        self.status.setText(f"Export {'Success' if ok else 'Failed'}\nOutput: {out_dir}\n\n{log}")

    def import_paloc(self):
        out_dir = BASE_DIR / "PALOC_Import"
        out_dir.mkdir(exist_ok=True)

        ok, log = run_command(
            [sys.executable, str(TOOLS_DIR / "paloc_Tool.py"), self.json.text()],
            cwd=out_dir
        )

        self.progress.setValue(100 if ok else 0)
        self.status.setText(f"Import {'Success' if ok else 'Failed'}\nOutput: {out_dir}\n\n{log}")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Crimson Desert Localization Tool")
        self.resize(920, 620)

        self.layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        if CONFIG["first_run"]:
            self.tabs.addTab(SettingsPage(self), "Settings")
        else:
            self.open_main_tabs()

        credit = QLabel("Crimson Desert Localization Tool | by newone9852 (translator)\n(Do not support people who use my tools to sell mods.)")
        credit.setStyleSheet("color: gray; font-size: 11px;")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.layout.addWidget(credit)

    def open_main_tabs(self):
        self.tabs.clear()
        self.tabs.addTab(LocalizationPage(), "Localization")
        self.tabs.addTab(FontsPage(), "Fonts")
        self.tabs.addTab(PalocPage(), "PALOC")
        self.tabs.addTab(SettingsPage(self), "Settings")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())