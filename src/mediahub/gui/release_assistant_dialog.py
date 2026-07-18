from __future__ import annotations

import shutil
import sys
from pathlib import Path


def _mediahub_utf8_env():
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
)

from src.mediahub.security.maintenance_gate import gate_exists, verify_password


class ReleaseAssistantDialog(QDialog):
    """Developer dialog for MediaHub release tasks.

    Important: this dialog intentionally uses the existing project scripts instead of
    re-implementing build logic here. The one-click release button calls
    build_release.py when available, otherwise build.py.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_dir = Path(__file__).resolve().parents[3]
        self.process: QProcess | None = None
        self.command_queue: list[tuple[str, list[str]]] = []
        self.current_step = ""
        self.release_notes_path = self.root_dir / "RELEASE_NOTES_PENDING.md"
        self.release_notes_text = ""
        self.release_commit_message = ""

        self.setWindowTitle("MediaHub Release Assistant")
        self.resize(980, 720)
        self.setMinimumSize(820, 560)

        self._build_ui()
        self.refresh_status()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        self.setStyleSheet(
            """
            QDialog {
                background: #151820;
                color: #f3f4f8;
                font-family: Segoe UI, Arial;
                font-size: 10pt;
            }
            QLabel#TitleLabel {
                font-size: 22pt;
                font-weight: 800;
                color: #ffffff;
            }
            QLabel#SubtitleLabel {
                font-size: 10pt;
                color: #cbd2e1;
            }
            QFrame#HeaderFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #242b3d, stop:1 #513354);
                border: 1px solid #3a4156;
                border-radius: 16px;
            }
            QGroupBox {
                border: 1px solid #30384b;
                border-radius: 12px;
                margin-top: 14px;
                padding: 14px;
                background: #1c2130;
                font-weight: 700;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 8px;
            }
            QPushButton {
                background: #2a3246;
                border: 1px solid #46516b;
                border-radius: 10px;
                padding: 9px 14px;
                color: #ffffff;
                font-weight: 650;
            }
            QPushButton:hover { background: #34405b; }
            QPushButton:pressed { background: #20283a; }
            QPushButton:disabled { color: #8b91a3; background: #242936; border-color: #333a4c; }
            QPushButton#PrimaryButton {
                background: #d66a2c;
                border: 1px solid #ff995e;
                color: #ffffff;
                font-size: 12pt;
                font-weight: 800;
                padding: 13px 18px;
            }
            QPushButton#PrimaryButton:hover { background: #ee7d39; }
            QPushButton#DangerButton {
                background: #74313d;
                border: 1px solid #ad5262;
            }
            QPlainTextEdit {
                background: #0f1219;
                color: #e8edf8;
                border: 1px solid #30384b;
                border-radius: 10px;
                padding: 10px;
                font-family: Consolas, Cascadia Mono, monospace;
                font-size: 9.5pt;
            }
            """
        )

        header = QFrame()
        header.setObjectName("HeaderFrame")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)

        title = QLabel("🚀 MediaHub Release Assistant")
        title.setObjectName("TitleLabel")
        subtitle = QLabel(f"Developer-Bereich · Projekt: {self.root_dir}")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        status_box = QGroupBox("📦 Status")
        status_layout = QGridLayout(status_box)
        status_layout.setColumnStretch(1, 1)
        self.status_labels: dict[str, QLabel] = {}
        rows = [
            ("project", "Projekt"),
            ("docs", "Dokumentation"),
            ("build", "Build-Skripte"),
            ("tools", "Werkzeuge"),
            ("git", "Git"),
            ("github", "GitHub"),
            ("licenses", "Lizenzen"),
        ]
        for row, (key, label) in enumerate(rows):
            status_layout.addWidget(QLabel(label + ":"), row, 0)
            value = QLabel("wird geprüft ...")
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.status_labels[key] = value
            status_layout.addWidget(value, row, 1)
        root.addWidget(status_box)

        actions_box = QGroupBox("🔨 Aktionen")
        actions = QGridLayout(actions_box)
        actions.setSpacing(10)

        self.btn_refresh = QPushButton("🔄 Status prüfen")
        self.btn_docs = QPushButton("📖 Handbücher bauen")
        self.btn_build = QPushButton("⚙ MediaHub bauen")
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("Neue Version, z. B. 1.0.4")
        try:
            from src.mediahub.app_info import APP_VERSION
            self.version_input.setText(APP_VERSION)
        except Exception:
            pass
        self.btn_release = QPushButton("🚀 Komplettes Release veröffentlichen")
        self.btn_release.setObjectName("PrimaryButton")
        self.btn_git_status = QPushButton("🔎 Git Status")
        self.btn_git_add = QPushButton("➕ Änderungen vormerken")
        self.btn_git_commit = QPushButton("💾 Commit erstellen")
        self.btn_git_push = QPushButton("☁ Push zu GitHub")
        self.btn_clear_log = QPushButton("🧹 Log leeren")
        self.btn_close = QPushButton("Schließen")

        actions.addWidget(QLabel("Neue Version:"), 0, 0)
        actions.addWidget(self.version_input, 0, 1, 1, 2)
        actions.addWidget(self.btn_release, 0, 3)
        actions.addWidget(self.btn_refresh, 1, 0)
        actions.addWidget(self.btn_docs, 1, 1)
        actions.addWidget(self.btn_build, 1, 2)
        actions.addWidget(self.btn_git_status, 2, 0)
        actions.addWidget(self.btn_git_add, 2, 1)
        actions.addWidget(self.btn_git_commit, 2, 2)
        actions.addWidget(self.btn_git_push, 2, 3)
        actions.addWidget(self.btn_clear_log, 3, 0)
        actions.addWidget(self.btn_close, 3, 3)
        root.addWidget(actions_box)

        log_box = QGroupBox("📋 Log")
        log_layout = QVBoxLayout(log_box)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        log_layout.addWidget(self.log)
        root.addWidget(log_box, 1)

        self.btn_refresh.clicked.connect(self.refresh_status)
        self.btn_docs.clicked.connect(lambda: self.run_commands([("Handbücher bauen", self.python_cmd("build_docs.py"))]))
        self.btn_build.clicked.connect(lambda: self.run_commands([("MediaHub bauen", self.python_cmd("build.py"))]))
        self.btn_release.clicked.connect(self.release_one_click)
        self.btn_git_status.clicked.connect(lambda: self.run_commands([("Git Status", ["git", "status", "--short", "--branch"])]))
        self.btn_git_add.clicked.connect(self.git_add)
        self.btn_git_commit.clicked.connect(self.git_commit)
        self.btn_git_push.clicked.connect(self.git_push)
        self.btn_clear_log.clicked.connect(self.log.clear)
        self.btn_close.clicked.connect(self.close)

    def python_cmd(self, script_name: str) -> list[str]:
        return [sys.executable, str(self.root_dir / script_name)]

    def set_status(self, key: str, text: str):
        self.status_labels[key].setText(text)

    def refresh_status(self):
        self.append_log("\n=== Statusprüfung ===")
        main_py = self.root_dir / "main.py"
        icon = self.root_dir / "assets" / "icons" / "mediahub.ico"
        version_file = self.root_dir / "version_info.txt"
        self.set_status("project", self.ok_warn([main_py.exists(), icon.exists()], f"main.py: {main_py.exists()} · Icon: {icon.exists()} · Versiondatei: {version_file.exists()}"))

        docs_src = self.root_dir / "docs"
        docs_assets = self.root_dir / "assets" / "docs"
        self.set_status("docs", self.ok_warn([docs_src.exists() or docs_assets.exists()], f"docs/: {docs_src.exists()} · assets/docs/: {docs_assets.exists()}"))

        scripts = ["build.py", "build_docs.py", "build_release.py"]
        self.set_status("build", self.ok_warn([(self.root_dir / s).exists() for s in scripts], " · ".join(f"{s}: {(self.root_dir / s).exists()}" for s in scripts)))

        pyinstaller = shutil.which("pyinstaller") or shutil.which("PyInstaller")
        git = shutil.which("git")
        self.set_status("tools", self.ok_warn([bool(pyinstaller), bool(git)], f"PyInstaller: {bool(pyinstaller)} · Git: {bool(git)}"))

        git_dir = self.root_dir / ".git"
        self.set_status("git", "✔ Repository erkannt" if git_dir.exists() else "⚠ Kein .git-Ordner gefunden")

        github_ok = False
        git_config = self.root_dir / ".git" / "config"
        if git_config.exists():
            try:
                github_ok = "github.com" in git_config.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception:
                github_ok = False
        self.set_status("github", "✔ GitHub-Remote gefunden" if github_ok else "⚠ GitHub-Remote nicht erkannt")

        license_paths = [
            self.root_dir / "THIRD_PARTY_NOTICES.md",
            self.root_dir / "THIRD_PARTY_LICENSES.md",
            self.root_dir / "licenses" / "Apache-2.0.txt",
            self.root_dir / "licenses" / "BSD-2-Clause.txt",
            self.root_dir / "licenses" / "GPL-2.0.txt",
            self.root_dir / "licenses" / "LGPL-3.0.txt",
            self.root_dir / "licenses" / "MIT.txt",
            self.root_dir / "licenses" / "Unlicense.txt",
        ]
        licenses_ok = all(path.exists() and path.stat().st_size > 0 for path in license_paths)
        self.set_status("licenses", "✔ Pflicht-Lizenzdateien vollständig" if licenses_ok else "⚠ Pflicht-Lizenzdateien fehlen")

        self.load_release_notes()

        self.append_log("Statusprüfung fertig.")

    def load_release_notes(self) -> None:
        self.release_notes_text = ""
        self.release_commit_message = ""

        if self.release_notes_path.exists():
            try:
                self.release_notes_text = self.release_notes_path.read_text(
                    encoding="utf-8"
                ).strip()
            except Exception as error:
                self.append_log(f"Release-Notizen konnten nicht gelesen werden: {error}")

        self.release_commit_message = self.extract_commit_message(
            self.release_notes_text
        )

    @staticmethod
    def extract_commit_message(text: str) -> str:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.strip().lower() == "## commit-nachricht":
                for candidate in lines[index + 1:]:
                    candidate = candidate.strip()
                    if candidate and not candidate.startswith("#"):
                        return candidate
                break
        return ""

    def finish_successful_release(self) -> None:
        if self.release_notes_path.exists():
            try:
                self.release_notes_path.unlink()
                self.append_log(
                    "RELEASE_NOTES_PENDING.md wurde nach erfolgreichem Release gelöscht."
                )
            except Exception as error:
                self.append_log(
                    f"WARNUNG: Release-Notizen konnten nicht gelöscht werden: {error}"
                )
        self.refresh_status()

    def ok_warn(self, checks: list[bool], detail: str) -> str:
        prefix = "✔" if all(checks) else "⚠"
        return f"{prefix} {detail}"

    def release_one_click(self):
        version = self.version_input.text().strip().lstrip("v")
        if not version:
            QMessageBox.warning(self, "Version fehlt", "Bitte eine neue Versionsnummer eingeben, zum Beispiel 1.0.4.")
            return

        required_licenses = [
            self.root_dir / "THIRD_PARTY_NOTICES.md",
            self.root_dir / "THIRD_PARTY_LICENSES.md",
            self.root_dir / "licenses" / "Apache-2.0.txt",
            self.root_dir / "licenses" / "BSD-2-Clause.txt",
            self.root_dir / "licenses" / "GPL-2.0.txt",
            self.root_dir / "licenses" / "LGPL-3.0.txt",
            self.root_dir / "licenses" / "MIT.txt",
            self.root_dir / "licenses" / "Unlicense.txt",
        ]
        missing_licenses = [str(path.relative_to(self.root_dir)) for path in required_licenses if not path.exists() or path.stat().st_size == 0]
        if missing_licenses:
            QMessageBox.critical(
                self,
                "Lizenzprüfung fehlgeschlagen",
                "Das Release wurde nicht gestartet. Fehlende oder leere Lizenzdateien:\n\n"
                + "\n".join(missing_licenses),
            )
            self.append_log("Release abgebrochen: Lizenzprüfung fehlgeschlagen.")
            return

        script = self.root_dir / "publish_release.py"
        if not script.exists():
            QMessageBox.critical(self, "Datei fehlt", "publish_release.py wurde nicht gefunden.")
            return

        self.load_release_notes()
        if not self.release_notes_text:
            QMessageBox.warning(
                self,
                "Release-Notizen fehlen",
                "RELEASE_NOTES_PENDING.md wurde nicht gefunden oder ist leer.\n\n"
                "Das Release wurde nicht gestartet.",
            )
            self.append_log("Release abgebrochen: Release-Notizen fehlen.")
            return

        if not self._confirm_release_overview(version):
            self.append_log("Release-Veröffentlichung abgebrochen.")
            return

        if not self._confirm_release_password(version):
            return

        self.run_commands(
            [(f"MediaHub v{version} vollständig veröffentlichen", [sys.executable, str(script), version])],
            after_finish=self.finish_successful_release,
        )


    def _confirm_release_overview(self, version: str) -> bool:
        """Zeigt eine kompakte, scrollbar aufgebaute Release-Bestätigung."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Komplettes Release veröffentlichen")
        dialog.resize(760, 520)
        dialog.setMinimumSize(640, 420)
        dialog.setMaximumHeight(680)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        heading = QLabel(f"MediaHub v{version} vollständig veröffentlichen?")
        heading.setStyleSheet("font-size: 14pt; font-weight: 800;")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        explanation = QLabel(
            "Der Assistent aktualisiert die Version, baut EXE, Setup und "
            "Handbücher, erstellt Commit und Tag und überträgt alles zu "
            "GitHub. Danach folgt die zweite Passwortabfrage."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        notes_label = QLabel("Folgende Release-Notizen werden verwendet:")
        notes_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(notes_label)

        notes = QPlainTextEdit()
        notes.setReadOnly(True)
        notes.setPlainText(self.release_notes_text)
        notes.setMinimumHeight(220)
        notes.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        notes.moveCursor(notes.textCursor().MoveOperation.Start)
        layout.addWidget(notes, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes
            | QDialogButtonBox.StandardButton.Cancel
        )
        yes_button = buttons.button(QDialogButtonBox.StandardButton.Yes)
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if yes_button is not None:
            yes_button.setText("Ja, weiter zur Passwortabfrage")
            yes_button.setDefault(False)
            yes_button.setAutoDefault(False)
        if cancel_button is not None:
            cancel_button.setText("Abbrechen")
            cancel_button.setDefault(True)
            cancel_button.setAutoDefault(True)

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        return dialog.exec() == QDialog.DialogCode.Accepted

    def _confirm_release_password(self, version: str) -> bool:
        """Verlangt unmittelbar vor der Veröffentlichung einen neuen Einmal-Code."""
        if not gate_exists(self.root_dir):
            QMessageBox.warning(
                self,
                "Release-Freigabe",
                "A.A.A.\n\nDu hast das Zauberwort nicht gesagt.\n\nA.A.A. NEIN!",
            )
            self.append_log("Release abgebrochen: Passwortschutz ist nicht eingerichtet.")
            return False

        password, accepted = QInputDialog.getText(
            self,
            "Release endgültig freigeben",
            f"MediaHub v{version} wird gleich zu GitHub übertragen.\n\n"
            "Bitte dafür ein NEUES Einmal-Passwort eingeben:",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            self.append_log("Release-Veröffentlichung bei der Passwortabfrage abgebrochen.")
            return False

        if not verify_password(self.root_dir, password):
            QMessageBox.warning(
                self,
                "Release-Freigabe verweigert",
                "Einmal-Passwort falsch oder bereits verbraucht.\n\n"
                "Es wurden keine Build-, Git- oder GitHub-Schritte gestartet.",
            )
            self.append_log("Release abgebrochen: Einmal-Passwort falsch oder bereits verbraucht.")
            return False

        self.append_log(f"Release v{version} durch neues Einmal-Passwort freigegeben.")
        return True

    def git_add(self):
        answer = QMessageBox.question(
            self,
            "Änderungen vormerken",
            "Alle Änderungen mit 'git add -A' vormerken?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.run_commands([("Git add", ["git", "add", "-A"]), ("Git Status", ["git", "status", "--short", "--branch"])])

    def git_commit(self):
        self.load_release_notes()
        default_message = self.release_commit_message or ""
        message, ok = QInputDialog.getText(
            self,
            "Commit erstellen",
            "Commit-Nachricht:",
            QLineEdit.EchoMode.Normal,
            default_message,
        )
        message = message.strip()
        if ok and message:
            self.run_commands([("Git commit", ["git", "commit", "-m", message]), ("Git Status", ["git", "status", "--short", "--branch"])])

    def git_push(self):
        answer = QMessageBox.question(
            self,
            "Push zu GitHub",
            "Aktuellen Branch zu GitHub pushen?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.run_commands([("Git push", ["git", "push"]), ("Git Status", ["git", "status", "--short", "--branch"])])

    def run_commands(self, commands: list[tuple[str, list[str]]], after_finish=None):
        if self.process is not None:
            QMessageBox.warning(self, "Prozess läuft", "Es läuft bereits ein Vorgang.")
            return
        self.after_finish = after_finish
        self.command_queue = list(commands)
        self.set_buttons_enabled(False)
        self.run_next_command()

    def run_next_command(self):
        if not self.command_queue:
            self.append_log("\n=== Vorgang fertig ===")
            self.process = None
            self.set_buttons_enabled(True)
            callback = getattr(self, "after_finish", None)
            self.after_finish = None
            if callback:
                callback()
            return

        self.current_step, command = self.command_queue.pop(0)
        self.append_log(f"\n=== {self.current_step} ===")
        self.append_log("$ " + " ".join(str(c) for c in command))

        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(self.root_dir))

        environment = QProcessEnvironment.systemEnvironment()
        if self.release_notes_path.exists():
            environment.insert(
                "MEDIAHUB_RELEASE_NOTES_FILE",
                str(self.release_notes_path),
            )
            environment.insert(
                "MEDIAHUB_RELEASE_COMMIT_MESSAGE",
                self.release_commit_message,
            )
        self.process.setProcessEnvironment(environment)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.on_process_output)
        self.process.finished.connect(self.on_process_finished)
        self.process.start(command[0], command[1:])

    def on_process_output(self):
        if not self.process:
            return
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.append_log(data.rstrip())

    def on_process_finished(self, exit_code: int, exit_status):
        failed = exit_code != 0
        self.append_log(f"\n{self.current_step} beendet mit Code {exit_code}.")
        self.process = None
        if failed:
            self.append_log("Vorgang abgebrochen, weil ein Schritt fehlgeschlagen ist.")
            self.command_queue.clear()
            self.set_buttons_enabled(True)
            return
        self.run_next_command()

    def set_buttons_enabled(self, enabled: bool):
        for button in [
            self.btn_refresh,
            self.btn_docs,
            self.btn_build,
            self.btn_release,
            self.btn_git_status,
            self.btn_git_add,
            self.btn_git_commit,
            self.btn_git_push,
            self.btn_clear_log,
            self.btn_close,
            self.version_input,
        ]:
            button.setEnabled(enabled)

    def append_log(self, text: str):
        self.log.appendPlainText(text)
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
