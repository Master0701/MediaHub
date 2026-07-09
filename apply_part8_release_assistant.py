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

        # Wenn die ZIP direkt in den MediaHub-Ordner entpackt wurde,
        # sind Quelle und Ziel identisch. Dann darf NICHT kopiert werden.
        if _same_file(src, dst):
            print(f"OK Datei liegt bereits richtig: {rel}")
            continue

        if dst.exists():
            backup = dst.with_name(dst.name + ".part8_backup")
            if not backup.exists():
                try:
                    shutil.copy2(dst, backup)
                    print(f"OK Backup erstellt: {backup.relative_to(TARGET)}")
                except Exception:
                    print(f"WARN Backup konnte nicht erstellt werden: {dst}")

        try:
            shutil.copy2(src, dst)
            print(f"OK Datei kopiert: {rel}")
        except PermissionError as error:
            raise PermissionError(
                "Datei ist gesperrt und konnte nicht ersetzt werden:\n"
                f"  {dst}\n\n"
                "Bitte MediaHub, alle python.exe-Prozesse, VS Code/Vorschau-Fenster "
                "und Explorer-Vorschau schließen und dann erneut starten."
            ) from error


def patch_gitignore() -> None:
    path = TARGET / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    additions = ["config/.mh_gate.json", "config/mh_gate.json"]
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
        raise FileNotFoundError(f"main_window.py nicht gefunden: {path}")

    text = path.read_text(encoding="utf-8")
    original = text

    import_line = "from src.mediahub.gui.release_gate import open_release_assistant_with_gate"
    if import_line not in text:
        marker = "from src.mediahub.gui.plugin_center import PluginCenter"
        if marker in text:
            text = text.replace(marker, marker + "\n" + import_line, 1)
        else:
            text = import_line + "\n" + text

    # Methode in MainWindow einfuegen. Marker ist in deinem aktuellen Stand vorhanden.
    if "def open_release_assistant(self):" not in text:
        method = (
            "\n    def open_release_assistant(self):\n"
            "        open_release_assistant_with_gate(self, self.base_dir, APP_VERSION)\n"
        )
        marker = "    def open_tool_center(self):"
        if marker in text:
            text = text.replace(marker, method + "\n" + marker, 1)
        else:
            marker = "    def open_setup_wizard(self):"
            if marker in text:
                text = text.replace(marker, method + "\n" + marker, 1)
            else:
                text += method

    # Extras-Menue einfuegen, ohne bestehende Werkzeuge/Hilfe kaputtzumachen.
    if "Release-Assistent" not in text:
        extra_block = (
            "\n        extras_menu = menu.addMenu(\"Extras\")\n"
            "        extras_menu.addAction(\"Release-Assistent\", self.open_release_assistant)\n"
        )
        marker = "        help_menu = menu.addMenu(\"Hilfe\")"
        if marker in text:
            text = text.replace(marker, extra_block + "\n" + marker, 1)
        else:
            marker = "        tools_menu.addAction(\"Download abbrechen\", self.cancel_download)"
            if marker in text:
                text = text.replace(marker, marker + extra_block, 1)
            else:
                raise RuntimeError("Konnte passende Stelle fuer Extras-Menue nicht finden.")

    if text != original:
        backup = path.with_suffix(".py.part8_backup")
        if not backup.exists():
            backup.write_text(original, encoding="utf-8")
            print(f"OK Backup erstellt: {backup.relative_to(TARGET)}")
        try:
            path.write_text(text, encoding="utf-8")
        except PermissionError as error:
            raise PermissionError(
                "main_window.py ist gesperrt. Bitte MediaHub/Python/Editor schließen und erneut starten."
            ) from error
        print("OK main_window.py erweitert")
    else:
        print("OK main_window.py war bereits erweitert")


def main() -> int:
    print("MediaHub Teil 8: Release-Assistent installieren")
    print(f"Zielordner: {TARGET}")
    copy_files()
    patch_gitignore()
    patch_main_window()
    print("")
    print("Fertig.")
    print("Jetzt Passwort einrichten:")
    print("  python tools/mediahub_password_tool.py")
    print("")
    print("Danach MediaHub starten und im Menue Extras -> Release-Assistent oeffnen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
