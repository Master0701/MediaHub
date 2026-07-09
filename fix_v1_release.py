from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAIN_WINDOW = ROOT / "src" / "mediahub" / "gui" / "main_window.py"


REPLACEMENTS = [
    ("from src.mediahub.gui.bulk_renamer_panel import BulkRenamerPanel\n", ""),

    ("        self.bulk_renamer_panel = None\n", ""),

    ("        tools_menu.addAction(\"Bulk Renamer\", self.open_bulk_renamer)\n", ""),

    ("        self.bulk_renamer_panel = BulkRenamerPanel(base_dir=self.base_dir, parent=self)\n", ""),

    ("            self.bulk_renamer_panel,\n", ""),

    ("        self._add_page(\"🔤 Bulk Renamer\", self.bulk_renamer_panel)\n", ""),

    ("            \"Bulk Renamer\": \"Dateien und Ordner massenhaft mit Vorschau umbenennen.\",\n", ""),

    ("            \"Bulk Renamer\": \"tools\",\n", ""),

    ("            (\"Bulk Renamer öffnen\", self.open_bulk_renamer),\n", ""),

    (
        '''    def open_bulk_renamer(self):
        self._select_nav_page("Bulk Renamer")

''',
        "",
    ),

    (
        '''    def open_plugin_by_id(self, plugin_id):
        if plugin_id == "bulk_renamer":
            self.open_bulk_renamer()
        else:
            QMessageBox.information(self, "Plugin", f"Für dieses Plugin ist noch keine sichere MediaHub-Aktion hinterlegt:\\n{plugin_id}")

''',
        '''    def open_plugin_by_id(self, plugin_id):
        QMessageBox.information(
            self,
            "Plugin",
            f"Dieses Plugin ist in MediaHub v1.0 noch nicht als ausführbares Plugin verfügbar:\\n{plugin_id}"
        )

''',
    ),
]


def main():
    if not MAIN_WINDOW.exists():
        print(f"❌ Datei nicht gefunden: {MAIN_WINDOW}")
        return

    text = MAIN_WINDOW.read_text(encoding="utf-8")
    original = text

    for old, new in REPLACEMENTS:
        text = text.replace(old, new)

    if text == original:
        print("⚠ Keine Änderungen durchgeführt. Datei war vielleicht schon bereinigt.")
    else:
        MAIN_WINDOW.write_text(text, encoding="utf-8")
        print("✅ main_window.py für MediaHub v1.0 bereinigt.")

    print()
    print("Bitte danach löschen/umbenennen:")
    print(" - plugins\\bulk_renamer")
    print(" - src\\mediahub\\gui\\bulk_renamer_panel.py")


if __name__ == "__main__":
    main()