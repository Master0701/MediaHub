from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ReleaseAssistantDialog(QDialog):
    """Interner Release-Assistent fuer MediaHub."""

    def __init__(self, base_dir: Path | str, app_version: str = "v1.0.0", parent=None):
        super().__init__(parent)
        self.base_dir = Path(base_dir)
        self.app_version = app_version
        self.status_labels: dict[str, QLabel] = {}

        self.setWindowTitle("Release-Assistent")
        self.resize(760, 560)
        self.setMinimumSize(620, 420)

        layout = QVBoxLayout(self)

        title = QLabel("🚀 MediaHub Release-Assistent")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel(
            "Prüft die wichtigsten Punkte vor einem Release und kann den vorhandenen Release-Build starten."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        box = QGroupBox("Release-Check")
        box_layout = QVBoxLayout(box)
        for key, label in [
            ("version", "Version"),
            ("docs", "Handbücher aktuell"),
            ("exe", "EXE gebaut"),
            ("setup", "Setup gebaut"),
            ("git", "Git sauber"),
            ("github", "GitHub verbunden"),
        ]:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            name = QLabel(label)
            name.setMinimumWidth(190)
            value = QLabel("…")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row_layout.addWidget(name)
            row_layout.addWidget(value, 1)
            box_layout.addWidget(row)
            self.status_labels[key] = value
        layout.addWidget(box)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Release-Ausgabe erscheint hier …")
        layout.addWidget(self.output, 1)

        button_row = QHBoxLayout()
        self.btn_refresh = QPushButton("Status prüfen")
        self.btn_release = QPushButton("🚀 Release erstellen")
        self.btn_close = QPushButton("Schließen")
        self.btn_refresh.clicked.connect(self.refresh_status)
        self.btn_release.clicked.connect(self.create_release)
        self.btn_close.clicked.connect(self.close)
        button_row.addWidget(self.btn_refresh)
        button_row.addStretch(1)
        button_row.addWidget(self.btn_release)
        button_row.addWidget(self.btn_close)
        layout.addLayout(button_row)

        self.refresh_status()

    def _set(self, key: str, ok: bool | None, text: str) -> None:
        prefix = "✔" if ok is True else "✖" if ok is False else "•"
        self.status_labels[key].setText(f"{prefix} {text}")

    def _run(self, args: list[str], timeout: int = 20) -> tuple[int, str]:
        try:
            result = subprocess.run(
                args,
                cwd=str(self.base_dir),
                text=True,
                capture_output=True,
                timeout=timeout,
                shell=False,
            )
            return result.returncode, (result.stdout or "") + (result.stderr or "")
        except Exception as error:
            return 999, str(error)

    def refresh_status(self) -> None:
        self._set("version", True, str(self.app_version).lstrip("v"))

        manual_pdf = self.base_dir / "docs" / "MediaHub_Anleitung.pdf"
        docs_source = self.base_dir / "docs_source"
        docs_ok = manual_pdf.exists() or docs_source.exists()
        self._set("docs", docs_ok, "gefunden" if docs_ok else "nicht gefunden")

        exe_candidates = list((self.base_dir / "dist").glob("**/MediaHub*.exe")) if (self.base_dir / "dist").exists() else []
        self._set("exe", bool(exe_candidates), "gefunden" if exe_candidates else "noch nicht gebaut")

        setup_candidates = []
        for folder in ("installer", "dist", "release"):
            path = self.base_dir / folder
            if path.exists():
                setup_candidates.extend(path.glob("**/*Setup*.exe"))
                setup_candidates.extend(path.glob("**/*setup*.exe"))
        self._set("setup", bool(setup_candidates), "gefunden" if setup_candidates else "noch nicht gebaut")

        if (self.base_dir / ".git").exists() and shutil.which("git"):
            code, out = self._run(["git", "status", "--porcelain"], timeout=15)
            clean = code == 0 and not out.strip()
            self._set("git", clean, "sauber" if clean else "Änderungen vorhanden")
            code_remote, out_remote = self._run(["git", "remote", "-v"], timeout=15)
            github_ok = code_remote == 0 and "github.com" in out_remote.lower()
            self._set("github", github_ok, "verbunden" if github_ok else "kein GitHub-Remote")
        else:
            self._set("git", False, "kein Git-Repo oder git fehlt")
            self._set("github", False, "nicht prüfbar")

    def create_release(self) -> None:
        self.output.clear()
        script = self.base_dir / "build_release.py"
        if not script.exists():
            QMessageBox.warning(self, "Release erstellen", f"build_release.py wurde nicht gefunden:\n{script}")
            return
        self.output.append("Starte Release-Build …\n")
        code, out = self._run([sys.executable, str(script)], timeout=120)
        self.output.append(out.strip() or "Keine Ausgabe.")
        if code == 0:
            self.output.append("\n✔ Release-Build abgeschlossen.")
            QMessageBox.information(self, "Release erstellen", "Release-Build abgeschlossen.")
        else:
            self.output.append(f"\n✖ Release-Build fehlgeschlagen. Code: {code}")
            QMessageBox.warning(self, "Release erstellen", "Release-Build fehlgeschlagen. Details stehen im Ausgabefeld.")
        self.refresh_status()
