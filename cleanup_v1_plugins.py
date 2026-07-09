from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAIN_WINDOW = ROOT / "src" / "mediahub" / "gui" / "main_window.py"
BULK_FILE = ROOT / "src" / "mediahub" / "gui" / "bulk_renamer_panel.py"
BULK_DEV_FILE = ROOT / "src" / "mediahub" / "gui" / "bulk_renamer_panel_dev.py"


def remove_lines_containing(text: str, keywords: list[str]) -> str:
    lines = text.splitlines()
    cleaned = []

    for line in lines:
        if any(keyword in line for keyword in keywords):
            continue
        cleaned.append(line)

    return "\n".join(cleaned) + "\n"


def main():
    if not MAIN_WINDOW.exists():
        print(f"❌ main_window.py nicht gefunden: {MAIN_WINDOW}")
        return

    text = MAIN_WINDOW.read_text(encoding="utf-8")

    keywords = [
        "bulk_renamer",
        "BulkRenamer",
        "Bulk Renamer",
        "bulk_renamer_panel",
    ]

    text = remove_lines_containing(text, keywords)

    safe_open_plugin = '''
    def open_plugin_by_id(self, plugin_id):
        QMessageBox.information(
            self,
            "Plugin",
            "Dieses Plugin wurde erkannt, wird in MediaHub v1.0 aber noch nicht direkt ausgeführt.\\n\\n"
            "Ab MediaHub 2.0 können Plugins eigene Fenster und Werkzeuge bereitstellen.\\n\\n"
            f"Plugin-ID: {plugin_id}"
        )
'''

    if "def open_plugin_by_id" not in text:
        insert_pos = text.rfind("\n")
        text = text[:insert_pos] + "\n" + safe_open_plugin + "\n" + text[insert_pos:]

    MAIN_WINDOW.write_text(text, encoding="utf-8")
    print("✅ main_window.py von Bulk-Renamer-Verweisen bereinigt.")

    if BULK_FILE.exists():
        if BULK_DEV_FILE.exists():
            BULK_FILE.unlink()
            print("✅ bulk_renamer_panel.py gelöscht, weil _dev-Datei schon existiert.")
        else:
            BULK_FILE.rename(BULK_DEV_FILE)
            print("✅ bulk_renamer_panel.py zu bulk_renamer_panel_dev.py umbenannt.")

    print("✅ MediaHub v1.0 ist jetzt ohne festen Bulk-Renamer vorbereitet.")


if __name__ == "__main__":
    main()