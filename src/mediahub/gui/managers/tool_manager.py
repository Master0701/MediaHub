from PySide6.QtWidgets import QMessageBox

from src.mediahub.gui.tool_center import ToolAssistant, ToolCenter


class ToolManager:
    def __init__(
        self,
        main_window,
        tool_service,
        log_panel,
        update_status_callback=None,
    ):
        self.main_window = main_window
        self.tool_service = tool_service
        self.log_panel = log_panel
        self.update_status = update_status_callback

    def open_tool_center(self):
        dialog = ToolCenter(self.tool_service, self.main_window)
        dialog.exec()

    def open_tool_assistant(self):
        dialog = ToolAssistant(self.tool_service, self.main_window)
        dialog.exec()

    def check_tools_on_start(self):
        missing = self.tool_service.missing_tools()

        if not missing:
            self.log_panel.write("Alle Tools gefunden.")
            return

        answer = QMessageBox.question(
            self.main_window,
            "Tools fehlen",
            "Es fehlen benötigte Tools im Ordner 'tools':\n\n"
            + "\n".join(missing)
            + "\n\nSoll MediaHub die fehlenden Tools automatisch herunterladen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            self.log_panel.write("Tools fehlen. Download-Funktionen sind eingeschränkt.")
            if self.update_status:
                self.update_status("Tools fehlen")
            return

        try:
            self.tool_service.download_missing_tools(self.log_panel.write)
            self.log_panel.write("Tool-Prüfung abgeschlossen.")
            if self.update_status:
                self.update_status("Tools geprüft")
        except Exception as error:
            self.log_panel.write(f"Fehler beim Tool-Download: {error}")
            if self.update_status:
                self.update_status("Fehler beim Tool-Download")