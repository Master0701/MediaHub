from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QLineEdit, QTextEdit, QListWidget, QListWidgetItem, QMessageBox,
    QGroupBox, QFormLayout, QSplitter, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt


class RecoveryCenter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = None
        self.backups = []
        self._build_ui()

    def set_manager(self, manager):
        self.manager = manager

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("🛟 Recovery Center")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Backups erstellen, vorhandene Sicherungen prüfen und MediaHub bei Problemen wiederherstellen."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(10)
        layout.addWidget(splitter, 1)

        # Linke Seite kommt in einen Scrollbereich. Dadurch werden die Knöpfe
        # nicht mehr zusammengeschoben, wenn das Fenster kleiner ist.
        left_content = QWidget()
        left_layout = QVBoxLayout(left_content)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(12)

        backup_group = QGroupBox("💾 Backup erstellen")
        backup_group.setMinimumWidth(360)
        form = QFormLayout(backup_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("z. B. Vor_grossem_Update")
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("Optionaler Kommentar")
        self.check_database = QCheckBox("Datenbank")
        self.check_config = QCheckBox("Konfiguration / Kanäle")
        self.check_logs = QCheckBox("Logs")
        self.check_downloads = QCheckBox("Downloads / Medien")
        self.check_database.setChecked(True)
        self.check_config.setChecked(True)

        form.addRow("Name:", self.name_input)
        form.addRow("Kommentar:", self.comment_input)
        form.addRow("Inhalt:", self.check_database)
        form.addRow("", self.check_config)
        form.addRow("", self.check_logs)
        form.addRow("", self.check_downloads)

        self.btn_create = QPushButton("Backup erstellen")
        self.btn_create.setMinimumHeight(34)
        self.btn_create.clicked.connect(self._create_backup)
        left_layout.addWidget(backup_group)
        left_layout.addWidget(self.btn_create)

        maintenance = QGroupBox("🧰 Wartung")
        maintenance.setMinimumWidth(360)
        maintenance_layout = QVBoxLayout(maintenance)
        maintenance_layout.setSpacing(8)
        self.btn_db_check = QPushButton("Datenbank prüfen")
        self.btn_db_cleanup = QPushButton("Datenbank bereinigen")
        self.btn_db_optimize = QPushButton("Datenbank optimieren / VACUUM")
        self.btn_orphans = QPushButton("Verwaiste Downloads suchen")
        self.btn_archive = QPushButton("Archiv prüfen")
        self.btn_db_check.clicked.connect(self._run_database_check)
        self.btn_db_cleanup.clicked.connect(self._cleanup_database)
        self.btn_db_optimize.clicked.connect(self._optimize_database)
        self.btn_orphans.clicked.connect(self._find_orphan_downloads)
        self.btn_archive.clicked.connect(self._check_archive)
        for button in (self.btn_db_check, self.btn_db_cleanup, self.btn_db_optimize, self.btn_orphans, self.btn_archive):
            button.setMinimumHeight(32)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            maintenance_layout.addWidget(button)
        left_layout.addWidget(maintenance)

        auto_backup = QGroupBox("⏱ Automatische Backups")
        auto_backup.setMinimumWidth(360)
        auto_layout = QVBoxLayout(auto_backup)
        auto_layout.setSpacing(8)
        auto_info = QLabel("Legt eine Backup-Aufgabe im Scheduler an. Inhalt: Datenbank + Konfiguration.")
        auto_info.setWordWrap(True)
        self.btn_auto_daily = QPushButton("Täglich planen")
        self.btn_auto_weekly = QPushButton("Wöchentlich planen")
        self.btn_auto_monthly = QPushButton("Monatlich planen")
        self.btn_auto_daily.clicked.connect(lambda: self._create_auto_backup_task(24))
        self.btn_auto_weekly.clicked.connect(lambda: self._create_auto_backup_task(24 * 7))
        self.btn_auto_monthly.clicked.connect(lambda: self._create_auto_backup_task(24 * 30))
        auto_layout.addWidget(auto_info)
        for button in (self.btn_auto_daily, self.btn_auto_weekly, self.btn_auto_monthly):
            button.setMinimumHeight(32)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            auto_layout.addWidget(button)
        left_layout.addWidget(auto_backup)
        selftest = QGroupBox("🧪 Selbsttest")
        selftest.setMinimumWidth(360)
        selftest_layout = QVBoxLayout(selftest)
        selftest_layout.setSpacing(8)
        selftest_info = QLabel("Prüft MediaHub automatisch und speichert einen Bericht im Log-Ordner.")
        selftest_info.setWordWrap(True)
        self.btn_selftest_quick = QPushButton("⚡ Schnelltest")
        self.btn_selftest_full = QPushButton("🔬 Volltest")
        self.btn_selftest_release = QPushButton("🚀 Release-Test")
        self.btn_selftest_report = QPushButton("📄 Letzten Bericht öffnen")
        self.btn_selftest_quick.clicked.connect(lambda: self._run_selftest("quick"))
        self.btn_selftest_full.clicked.connect(lambda: self._run_selftest("full"))
        self.btn_selftest_release.clicked.connect(lambda: self._run_selftest("release"))
        self.btn_selftest_report.clicked.connect(self._open_selftest_report)
        selftest_layout.addWidget(selftest_info)
        for button in (self.btn_selftest_quick, self.btn_selftest_full, self.btn_selftest_release, self.btn_selftest_report):
            button.setMinimumHeight(32)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            selftest_layout.addWidget(button)
        left_layout.addWidget(selftest)

        release_group = QGroupBox("🚀 Release Manager")
        release_group.setMinimumWidth(360)
        release_layout = QVBoxLayout(release_group)
        release_layout.setSpacing(8)
        release_info = QLabel(
            "Bereitet ein sauberes Release-Verzeichnis ohne private Kanäle, Logs oder Downloads vor."
        )
        release_info.setWordWrap(True)
        self.btn_release_prepare = QPushButton("📦 Release vorbereiten")
        self.btn_release_build = QPushButton("🚀 Release-ZIP bauen")
        self.btn_build_files = QPushButton("🪟 Build-Dateien erstellen")
        self.btn_release_clean_preview = QPushButton("🧹 Bereinigung prüfen")
        self.btn_release_report = QPushButton("📄 Release-Bericht öffnen")
        self.btn_release_prepare.clicked.connect(self._prepare_release)
        self.btn_release_build.clicked.connect(self._build_release_package)
        self.btn_build_files.clicked.connect(self._create_build_files)
        self.btn_release_clean_preview.clicked.connect(self._clean_runtime_preview)
        self.btn_release_report.clicked.connect(self._open_release_report)
        release_layout.addWidget(release_info)
        for button in (self.btn_release_prepare, self.btn_release_build, self.btn_build_files, self.btn_release_clean_preview, self.btn_release_report):
            button.setMinimumHeight(32)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            release_layout.addWidget(button)
        left_layout.addWidget(release_group)

        left_layout.addStretch(1)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        left_scroll.setWidget(left_content)
        left_scroll.setMinimumWidth(390)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(10)
        list_title = QLabel("📦 Vorhandene Backups")
        list_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.backup_list = QListWidget()
        self.backup_list.setMinimumHeight(220)
        self.backup_list.currentRowChanged.connect(self._show_selected_manifest)
        right_layout.addWidget(list_title)
        right_layout.addWidget(self.backup_list, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_restore = QPushButton("Wiederherstellen")
        self.btn_delete = QPushButton("Löschen")
        self.btn_open_folder = QPushButton("Backup-Ordner öffnen")
        self.btn_refresh.clicked.connect(self._refresh)
        self.btn_restore.clicked.connect(self._restore_backup)
        self.btn_delete.clicked.connect(self._delete_backup)
        self.btn_open_folder.clicked.connect(self._open_folder)
        for button in (self.btn_refresh, self.btn_restore, self.btn_delete, self.btn_open_folder):
            button.setMinimumHeight(32)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            buttons.addWidget(button)
        right_layout.addLayout(buttons)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(190)
        self.details.setMaximumHeight(260)
        right_layout.addWidget(self.details)

        splitter.addWidget(left_scroll)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([430, 760])

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(110)
        self.output.setMaximumHeight(180)
        layout.addWidget(QLabel("📋 Protokoll"))
        layout.addWidget(self.output)

    def load_backups(self, backups):
        self.backups = backups or []
        self.backup_list.clear()
        for item in self.backups:
            manifest = item.get("manifest") or {}
            created = manifest.get("created") or item.get("modified", "")
            size = self._format_size(item.get("size", 0))
            label = f"{item.get('name')}  ·  {size}  ·  {created}"
            list_item = QListWidgetItem(label)
            list_item.setData(Qt.ItemDataRole.UserRole, str(item.get("path")))
            self.backup_list.addItem(list_item)
        if self.backups:
            self.backup_list.setCurrentRow(0)
        else:
            self.details.setPlainText("Noch keine Backups vorhanden.")

    def append_output(self, message):
        self.output.append(str(message))

    def _create_backup(self):
        if self.manager is None:
            return
        self.output.clear()
        result = self.manager.create_backup(
            name=self.name_input.text().strip(),
            comment=self.comment_input.text().strip(),
            include_database=self.check_database.isChecked(),
            include_config=self.check_config.isChecked(),
            include_logs=self.check_logs.isChecked(),
            include_downloads=self.check_downloads.isChecked(),
        )
        QMessageBox.information(
            self,
            "Backup erstellt",
            f"Backup erfolgreich erstellt:\n{result.get('path')}\n\nGröße: {self._format_size(result.get('size', 0))}\nDauer: {result.get('duration', 0):.1f} Sekunden",
        )

    def _restore_backup(self):
        path = self._selected_path()
        if not path or self.manager is None:
            return
        answer = QMessageBox.question(
            self,
            "Backup wiederherstellen",
            "Dieses Backup stellt die config-Dateien wieder her.\n"
            "Vorher wird automatisch eine Sicherheitskopie erstellt.\n\n"
            "Fortfahren?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.output.clear()
        result = self.manager.restore_backup(path)
        QMessageBox.information(self, "Wiederherstellung", result.get("message", "Fertig"))

    def _delete_backup(self):
        path = self._selected_path()
        if not path or self.manager is None:
            return
        answer = QMessageBox.question(self, "Backup löschen", f"Backup wirklich löschen?\n{path}")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.manager.delete_backup(path)

    def _refresh(self):
        if self.manager is not None:
            self.manager.refresh()

    def _open_folder(self):
        if self.manager is not None:
            self.manager.open_backup_folder()

    def _selected_path(self):
        item = self.backup_list.currentItem()
        if item is None:
            return None
        return Path(item.data(Qt.ItemDataRole.UserRole))

    def _show_selected_manifest(self, index):
        if index < 0 or index >= len(self.backups):
            return
        item = self.backups[index]
        manifest = item.get("manifest") or {}
        includes = manifest.get("includes") or {}
        lines = [
            f"Datei: {item.get('name')}",
            f"Größe: {self._format_size(item.get('size', 0))}",
            f"MediaHub-Version: {manifest.get('mediahub_version', 'unbekannt')}",
            f"Backup-Version: {manifest.get('backup_version', 'unbekannt')}",
            f"Erstellt: {manifest.get('created', 'unbekannt')}",
            f"Kommentar: {manifest.get('comment', '')}",
            "",
            f"Kanäle: {manifest.get('channels', 0)}",
            f"Playlists: {manifest.get('playlists', 0)}",
            f"Videos: {manifest.get('videos', 0)}",
            f"Downloads: {manifest.get('downloads', 0)}",
            "",
            "Inhalt:",
            f"  Datenbank: {'ja' if includes.get('database') else 'nein'}",
            f"  Konfiguration: {'ja' if includes.get('config') else 'nein'}",
            f"  Logs: {'ja' if includes.get('logs') else 'nein'}",
            f"  Downloads: {'ja' if includes.get('downloads') else 'nein'}",
        ]
        self.details.setPlainText("\n".join(lines))


    def _run_database_check(self):
        self._run_manager_action("Datenbank prüfen", "run_database_check")

    def _cleanup_database(self):
        self._run_manager_action("Datenbank bereinigen", "cleanup_database")

    def _optimize_database(self):
        self._run_manager_action("Datenbank optimieren", "optimize_database")

    def _find_orphan_downloads(self):
        self._run_manager_action("Verwaiste Downloads suchen", "find_orphan_downloads")

    def _check_archive(self):
        self._run_manager_action("Archiv prüfen", "check_archive")

    def _create_auto_backup_task(self, interval_hours):
        if self.manager is None:
            return
        self.output.clear()
        task_id = self.manager.create_auto_backup_task(interval_hours)
        if task_id:
            QMessageBox.information(self, "Auto-Backup", "Auto-Backup wurde im Scheduler angelegt.")

    def _run_manager_action(self, title, method_name):
        if self.manager is None:
            return
        self.output.clear()
        method = getattr(self.manager, method_name)
        result = method()
        icon = QMessageBox.Icon.Information if result.get("ok") else QMessageBox.Icon.Warning
        box = QMessageBox(icon, title, result.get("message", "Fertig"), QMessageBox.StandardButton.Ok, self)
        details = "\n".join(str(x) for x in result.get("details", []))
        if details:
            box.setDetailedText(details)
        box.exec()


    def _run_selftest(self, mode):
        if self.manager is None:
            return
        self.output.clear()
        result = self.manager.run_selftest(mode)
        self.output.setPlainText(result.get("output", ""))
        if result.get("ok"):
            QMessageBox.information(self, "Selbsttest", result.get("message", "Selbsttest abgeschlossen."))
        else:
            box = QMessageBox(QMessageBox.Icon.Warning, "Selbsttest", result.get("message", "Selbsttest mit Fehlern beendet."), QMessageBox.StandardButton.Ok, self)
            if result.get("error"):
                box.setDetailedText(str(result.get("error")))
            box.exec()

    def _open_selftest_report(self):
        if self.manager is not None:
            self.manager.open_latest_selftest_report()


    def _prepare_release(self):
        if self.manager is None:
            return
        answer = QMessageBox.question(
            self,
            "Release vorbereiten",
            "MediaHub erstellt ein separates Release-Verzeichnis unter release_ready/.\n"
            "Deine aktuellen Daten werden dabei nicht gelöscht.\n\nFortfahren?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.output.clear()
        result = self.manager.prepare_release()
        text = result.get("message", "Release-Vorbereitung abgeschlossen.")
        if result.get("target"):
            text += f"\n\nZiel:\n{result.get('target')}"
        if result.get("warnings"):
            text += "\n\nWarnungen:\n" + "\n".join(result.get("warnings"))
        QMessageBox.information(self, "Release Manager", text)

    def _build_release_package(self):
        if self.manager is None:
            return
        answer = QMessageBox.question(
            self,
            "Release-ZIP bauen",
            "MediaHub erstellt ein frisches Release-Verzeichnis und packt es als ZIP.\n"
            "Deine aktuellen Arbeitsdaten werden nicht gelöscht.\n\nFortfahren?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.output.clear()
        result = self.manager.build_release_package()
        text = result.get("message", "Release-Paket erstellt.")
        if result.get("target"):
            text += f"\n\nOrdner:\n{result.get('target')}"
        if result.get("zip"):
            text += f"\n\nZIP:\n{result.get('zip')}"
        if result.get("warnings"):
            text += "\n\nWarnungen:\n" + "\n".join(result.get("warnings"))
        QMessageBox.information(self, "Release Builder", text)

    def _create_build_files(self):
        if self.manager is None:
            return
        self.output.clear()
        result = self.manager.create_build_files()
        QMessageBox.information(self, "Build-Dateien", result.get("message", "Build-Dateien erstellt."))

    def _clean_runtime_preview(self):
        if self.manager is None:
            return
        self.output.clear()
        result = self.manager.clean_runtime_preview()
        box = QMessageBox(QMessageBox.Icon.Information, "Bereinigung prüfen", result.get("message", "Fertig"), QMessageBox.StandardButton.Ok, self)
        details = "\n".join(str(x) for x in result.get("details", []))
        if details:
            box.setDetailedText(details)
        box.exec()

    def _open_release_report(self):
        if self.manager is not None:
            self.manager.open_latest_release_report()

    def _format_size(self, size):
        size = float(size or 0)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024
