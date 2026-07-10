from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

from src.mediahub.gui.release_assistant_dialog import ReleaseAssistantDialog
from src.mediahub.security.maintenance_gate import gate_exists, verify_password


class MaintenanceAccessDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zugriff prüfen")
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        label = QLabel("Bitte Einmal-Passwort eingeben:")
        layout.addWidget(label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.accept)
        layout.addWidget(self.password_input)

        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton("OK")
        cancel = QPushButton("Abbrechen")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        row.addWidget(ok)
        row.addWidget(cancel)
        layout.addLayout(row)

    @property
    def password(self) -> str:
        return self.password_input.text()


def open_release_assistant_with_gate(parent, base_dir: Path | str, app_version: str) -> None:
    base_path = Path(base_dir)
    if not gate_exists(base_path):
        QMessageBox.warning(
            parent,
            "Release-Assistent",
            "A.A.A.\n\n"
            "Du hast das Zauberwort nicht gesagt.\n\n"
            "A.A.A. NEIN!",
        )
        return

    dialog = MaintenanceAccessDialog(parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    if not verify_password(base_path, dialog.password):
        QMessageBox.warning(parent, "Release-Assistent", "Einmal-Passwort falsch oder bereits verbraucht.")
        return

    assistant = ReleaseAssistantDialog(parent)
    assistant.exec()
