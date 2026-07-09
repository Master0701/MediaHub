from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = Path.cwd()

FILES = [
    "src/mediahub/security/maintenance_gate.py",
    "src/mediahub/gui/release_assistant_dialog.py",
    "src/mediahub/gui/release_gate.py",
    "tools/mediahub_password_tool.py",
    "tools/build_password_tool_exe.py",
]


def _same_file(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except Exception:
        return False


def copy_files() -> None:
    for rel in FILES:
        src = ROOT / rel
        dst = TARGET / rel
        if not src.exists():
            raise FileNotFoundError(f"Paketdatei fehlt: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if _same_file(src, dst):
            print(f"OK Datei liegt bereits richtig: {rel}")
            continue
        if dst.exists():
            backup = dst.with_name(dst.name + ".part8_otp_backup")
            if not backup.exists():
                shutil.copy2(dst, backup)
                print(f"OK Backup erstellt: {backup.relative_to(TARGET)}")
        shutil.copy2(src, dst)
        print(f"OK Datei kopiert: {rel}")


def patch_gitignore() -> None:
    path = TARGET / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    additions = [
        "config/.mh_gate.json",
        "config/mh_gate.json",
        "private_tools/",
        "tools/__pycache__/",
        "*.spec",
    ]
    changed = False
    for item in additions:
        if item not in text:
            text += ("\n" if text and not text.endswith("\n") else "") + item + "\n"
            changed = True
    if changed:
        path.write_text(text, encoding="utf-8")
        print("OK .gitignore erweitert")
    else:
        print("OK .gitignore war bereits passend")


def patch_main_window() -> None:
    path = TARGET / "src" / "mediahub" / "gui" / "main_window.py"
    if not path.exists():
        print("WARN main_window.py nicht gefunden, Menü-Patch übersprungen.")
        return
    text = path.read_text(encoding="utf-8")
    original = text
    import_line = "from src.mediahub.gui.release_gate import open_release_assistant_with_gate"
    if import_line not in text:
        marker = "from src.mediahub.gui.plugin_center import PluginCenter"
        if marker in text:
            text = text.replace(marker, marker + "\n" + import_line, 1)
        else:
            text = import_line + "\n" + text
    if "def open_release_assistant(self):" not in text:
        method = (
            "\n    def open_release_assistant(self):\n"
            "        open_release_assistant_with_gate(self, self.base_dir, APP_VERSION)\n"
        )
        for marker in ("    def open_tool_center(self):", "    def open_setup_wizard(self):"):
            if marker in text:
                text = text.replace(marker, method + "\n" + marker, 1)
                break
        else:
            text += method
    if "Release-Assistent" not in text:
        extra_block = (
            "\n        extras_menu = menu.addMenu(\"Extras\")\n"
            "        extras_menu.addAction(\"Release-Assistent\", self.open_release_assistant)\n"
        )
        marker = "        help_menu = menu.addMenu(\"Hilfe\")"
        if marker in text:
            text = text.replace(marker, extra_block + "\n" + marker, 1)
        else:
            print("WARN Konnte Extras-Menü nicht automatisch einfügen.")
    if text != original:
        backup = path.with_suffix(".py.part8_otp_backup")
        if not backup.exists():
            backup.write_text(original, encoding="utf-8")
            print(f"OK Backup erstellt: {backup.relative_to(TARGET)}")
        path.write_text(text, encoding="utf-8")
        print("OK main_window.py geprüft/erweitert")
    else:
        print("OK main_window.py war bereits passend")


def main() -> int:
    print("MediaHub Teil 8.1: Einmal-Passwort fuer Release-Assistent installieren")
    print(f"Zielordner: {TARGET}")
    copy_files()
    patch_gitignore()
    patch_main_window()
    print("")
    print("Fertig.")
    print("Einmal-Gate einrichten/ersetzen:")
    print("  python tools/mediahub_password_tool.py --init --force")
    print("")
    print("Danach bei jedem Öffnen neuen Code anzeigen lassen:")
    print("  python tools/mediahub_password_tool.py")
    print("")
    print("Optional EXE bauen:")
    print("  python tools/build_password_tool_exe.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
