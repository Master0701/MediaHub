from __future__ import annotations

import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QProgressDialog,
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.mediahub.gui.ui_standards import (
    PANEL_MARGIN,
    PANEL_SPACING,
    configure_button,
    make_title,
)
from src.mediahub.services.ai_node_service import AINodeService
from src.mediahub.services.ai_node_provisioning_service import (
    AINodeProvisioningError,
    AINodeProvisioningService,
)
from src.mediahub.services.ai_plugin_catalog_service import AIPluginCatalogService
from src.mediahub.services.plugin_catalog_service import (
    CatalogPlugin,
    PluginCatalogService,
)
from src.mediahub.services.settings_service import SettingsService


class PluginStorePanel(QWidget):
    """Eingebetteter Plugin-Store für MediaHub- und AI-Plugins."""

    def __init__(
        self,
        base_dir: Path,
        plugin_loader,
        parent=None,
    ):
        super().__init__(parent)
        self.base_dir = Path(base_dir)
        self.plugin_loader = plugin_loader
        self.catalog_service = PluginCatalogService()
        self.ai_catalog_service = AIPluginCatalogService()
        self.settings_service = SettingsService(self.base_dir)

        self.mediahub_plugins: list[CatalogPlugin] = []
        self.ai_plugins: list[dict] = []

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            PANEL_MARGIN,
            PANEL_MARGIN,
            PANEL_MARGIN,
            PANEL_MARGIN,
        )
        layout.setSpacing(PANEL_SPACING)

        layout.addWidget(make_title("🛒 Plugin-Store"))

        info = QLabel(
            "MediaHub-Plugins laufen direkt in MediaHub. "
            "AI-Plugins laufen auf dem verbundenen Raspberry-Pi-AI-Node. "
            "Installations- und Updatezustände werden bei jedem Öffnen "
            "des Stores neu geprüft."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.tabs = QTabWidget()
        self.mediahub_tab = QWidget()
        self.ai_tab = QWidget()
        self.tabs.addTab(self.mediahub_tab, "MediaHub-Plugins")
        self.tabs.addTab(self.ai_tab, "AI-Plugins")
        layout.addWidget(self.tabs, 1)

        self._build_mediahub_tab()
        self._build_ai_tab()

        self.tabs.currentChanged.connect(self._tab_changed)

    def _build_mediahub_tab(self):
        layout = QVBoxLayout(self.mediahub_tab)

        self.mediahub_status = QLabel("Katalog wird geladen …")
        self.mediahub_status.setWordWrap(True)
        layout.addWidget(self.mediahub_status)

        filters = QHBoxLayout()

        self.mediahub_search = QLineEdit()
        self.mediahub_search.setPlaceholderText(
            "Plugins durchsuchen …"
        )

        self.mediahub_category_filter = QComboBox()
        self.mediahub_category_filter.addItem("Alle Kategorien")

        self.mediahub_state_filter = QComboBox()
        self.mediahub_state_filter.addItems(
            [
                "Alle Status",
                "Nicht installiert",
                "Installiert",
                "Update verfügbar",
                "Manuelle Installation",
                "Noch nicht installierbar",
            ]
        )

        self.mediahub_updates_only = QCheckBox(
            "Nur Updates"
        )

        filters.addWidget(self.mediahub_search, 2)
        filters.addWidget(self.mediahub_category_filter, 1)
        filters.addWidget(self.mediahub_state_filter, 1)
        filters.addWidget(self.mediahub_updates_only)

        layout.addLayout(filters)

        self.mediahub_list = QListWidget()
        self.mediahub_list.currentRowChanged.connect(
            self._show_mediahub_plugin
        )
        layout.addWidget(self.mediahub_list, 2)

        self.mediahub_details = QTextEdit()
        self.mediahub_details.setReadOnly(True)
        layout.addWidget(self.mediahub_details, 1)

        buttons = QHBoxLayout()
        self.btn_mediahub_refresh = configure_button(
            QPushButton("Katalog neu laden"),
            "Lädt den aktuellen MediaHub-Plugin-Katalog.",
        )
        self.btn_mediahub_project = configure_button(
            QPushButton("GitHub-Seite öffnen"),
            "Öffnet die Projektseite des ausgewählten Plugins.",
        )
        self.btn_mediahub_changelog = configure_button(
            QPushButton("Changelog öffnen"),
            "Öffnet die Änderungsübersicht des ausgewählten Plugins.",
        )
        self.btn_mediahub_install = configure_button(
            QPushButton("Installieren"),
            "Installiert das ausgewählte Plugin oder zeigt die manuelle Anleitung.",
        )

        self.mediahub_search.textChanged.connect(
            self.apply_mediahub_filters
        )
        self.mediahub_category_filter.currentTextChanged.connect(
            self.apply_mediahub_filters
        )
        self.mediahub_state_filter.currentTextChanged.connect(
            self.apply_mediahub_filters
        )
        self.mediahub_updates_only.stateChanged.connect(
            self.apply_mediahub_filters
        )

        self.btn_mediahub_refresh.clicked.connect(
            self.load_mediahub_catalog
        )
        self.btn_mediahub_project.clicked.connect(
            self.open_selected_project
        )
        self.btn_mediahub_changelog.clicked.connect(
            self.open_selected_changelog
        )
        self.btn_mediahub_install.clicked.connect(
            self.install_selected_mediahub_plugin
        )

        buttons.addWidget(self.btn_mediahub_refresh)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_mediahub_project)
        buttons.addWidget(self.btn_mediahub_changelog)
        buttons.addWidget(self.btn_mediahub_install)
        layout.addLayout(buttons)

    def _build_ai_tab(self):
        layout = QVBoxLayout(self.ai_tab)

        self.ai_status = QLabel("AI-Node wird geprüft …")
        self.ai_status.setWordWrap(True)
        layout.addWidget(self.ai_status)

        note = QLabel(
            "Hier werden installierte AI-Plugins des Raspberry-Pi-AI-Nodes "
            "und künftig veröffentlichte AI-Plugins aus dem GitHub-Katalog angezeigt."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.ai_catalog_status = QLabel("AI-Plugin-Store: Katalog noch nicht geladen.")
        self.ai_catalog_status.setWordWrap(True)
        layout.addWidget(self.ai_catalog_status)

        ai_filters = QHBoxLayout()

        self.ai_search = QLineEdit()
        self.ai_search.setPlaceholderText(
            "AI-Plugins durchsuchen …"
        )

        self.ai_state_filter = QComboBox()
        self.ai_state_filter.addItems(
            [
                "Alle Status",
                "Aktiviert",
                "Deaktiviert",
                "Geladen",
                "Nicht geladen",
                "Fehler",
            ]
        )

        ai_filters.addWidget(self.ai_search, 2)
        ai_filters.addWidget(self.ai_state_filter, 1)
        layout.addLayout(ai_filters)

        self.ai_list = QListWidget()
        self.ai_list.currentRowChanged.connect(
            self._show_ai_plugin
        )
        layout.addWidget(self.ai_list, 2)

        self.ai_details = QTextEdit()
        self.ai_details.setReadOnly(True)
        layout.addWidget(self.ai_details, 1)

        buttons = QHBoxLayout()
        self.btn_ai_catalog_refresh = configure_button(
            QPushButton("AI-Katalog aktualisieren"),
            "Lädt den AI-Plugin-Katalog aus GitHub.",
        )
        self.btn_ai_install = configure_button(
            QPushButton("AI-Plugin installieren"),
            "Wählt ein AI-Plugin-ZIP aus und erstellt auf dem Pi einen Installationsplan.",
        )
        self.btn_ai_refresh = configure_button(
            QPushButton("AI-Plugins neu laden"),
            "Lädt den aktuellen Plugin-Status vom AI-Node.",
        )
        self.btn_ai_enable = configure_button(
            QPushButton("Aktivieren"),
            "Aktiviert das ausgewählte AI-Plugin auf dem Pi.",
        )
        self.btn_ai_disable = configure_button(
            QPushButton("Deaktivieren"),
            "Deaktiviert das ausgewählte AI-Plugin auf dem Pi.",
        )
        self.btn_ai_remove = configure_button(
            QPushButton("Entfernen"),
            "Entfernt das ausgewählte AI-Plugin mit Sicherung.",
        )

        self.ai_search.textChanged.connect(
            self.apply_ai_filters
        )
        self.btn_ai_catalog_refresh.clicked.connect(self.load_ai_catalog)
        self.ai_state_filter.currentTextChanged.connect(
            self.apply_ai_filters
        )

        self.btn_ai_install.clicked.connect(
            self.install_ai_plugin_package
        )
        self.btn_ai_refresh.clicked.connect(self.load_ai_plugins)
        self.btn_ai_enable.clicked.connect(self.enable_selected_ai_plugin)
        self.btn_ai_disable.clicked.connect(self.disable_selected_ai_plugin)
        self.btn_ai_remove.clicked.connect(self.remove_selected_ai_plugin)

        buttons.addWidget(self.btn_ai_catalog_refresh)
        buttons.addWidget(self.btn_ai_install)
        buttons.addWidget(self.btn_ai_refresh)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_ai_enable)
        buttons.addWidget(self.btn_ai_disable)
        buttons.addWidget(self.btn_ai_remove)
        layout.addLayout(buttons)

        self._set_ai_action_buttons(False)

    def refresh(self):
        try:
            self.plugin_loader.discover()
        except Exception:
            pass
        self.load_mediahub_catalog()
        self.load_ai_catalog()
        self.load_ai_plugins()

    def _tab_changed(self, index: int):
        if self.tabs.widget(index) is self.ai_tab:
            self.load_ai_plugins()

    def _installed_mediahub_plugins(self) -> dict[str, object]:
        try:
            discovered = self.plugin_loader.discover()
        except Exception:
            return {}

        result = {}
        for plugin in discovered:
            plugin_id = str(
                getattr(plugin, "plugin_id", "")
                or getattr(plugin, "id", "")
            ).strip()
            if plugin_id:
                result[plugin_id] = plugin
        return result

    @staticmethod
    def _version_parts(value: str) -> tuple[int, ...]:
        parts = []
        for item in str(value).strip().lstrip("vV").split("."):
            digits = ""
            for character in item:
                if character.isdigit():
                    digits += character
                else:
                    break
            parts.append(int(digits or 0))
        return tuple(parts)

    def _mediahub_plugin_state(
        self,
        plugin: CatalogPlugin,
    ) -> tuple[str, str]:
        installed = self._installed_mediahub_plugins().get(
            plugin.plugin_id
        )
        if installed is None:
            return "not_installed", ""

        installed_version = str(
            getattr(installed, "version", "") or ""
        )
        if (
            self._version_parts(plugin.version)
            > self._version_parts(installed_version)
        ):
            return "update_available", installed_version

        return "installed", installed_version

    def _mediahub_state_text(
        self,
        plugin: CatalogPlugin,
    ) -> str:
        state, installed_version = self._mediahub_plugin_state(plugin)

        if state == "installed":
            return f"Installiert: v{installed_version}"
        if state == "update_available":
            return (
                f"Update verfügbar: v{installed_version} → "
                f"v{plugin.version}"
            )
        if plugin.manual_only:
            return "Manuelle Installation erforderlich"
        if not plugin.auto_install:
            return "Noch nicht installierbar"
        return "Nicht installiert"

    def load_mediahub_catalog(self):
        self.mediahub_list.clear()
        self.mediahub_details.clear()

        try:
            self.mediahub_plugins = (
                self.catalog_service.fetch_catalog()
            )
        except Exception as error:
            self.mediahub_plugins = []
            self.mediahub_status.setText(
                f"Plugin-Katalog konnte nicht geladen werden: {error}"
            )
            return

        categories = sorted(
            {
                str(
                    getattr(plugin, "category", "")
                    or "Erweiterung"
                )
                for plugin in self.mediahub_plugins
            }
        )

        current_category = self.mediahub_category_filter.currentText()
        self.mediahub_category_filter.blockSignals(True)
        self.mediahub_category_filter.clear()
        self.mediahub_category_filter.addItem("Alle Kategorien")
        self.mediahub_category_filter.addItems(categories)
        if current_category in categories:
            self.mediahub_category_filter.setCurrentText(
                current_category
            )
        self.mediahub_category_filter.blockSignals(False)

        self.apply_mediahub_filters()

    def apply_mediahub_filters(self):
        search = self.mediahub_search.text().strip().lower()
        category = self.mediahub_category_filter.currentText()
        state_filter = self.mediahub_state_filter.currentText()
        updates_only = self.mediahub_updates_only.isChecked()

        self.mediahub_list.clear()
        visible_plugins = []

        for plugin in self.mediahub_plugins:
            plugin_category = str(
                getattr(plugin, "category", "")
                or "Erweiterung"
            )
            state_text = self._mediahub_state_text(plugin)
            state_code, _ = self._mediahub_plugin_state(plugin)

            searchable = " ".join(
                [
                    plugin.name,
                    plugin.description,
                    plugin.plugin_id,
                    plugin_category,
                ]
            ).lower()

            if search and search not in searchable:
                continue

            if (
                category != "Alle Kategorien"
                and plugin_category != category
            ):
                continue

            if updates_only and state_code != "update_available":
                continue

            if state_filter == "Nicht installiert":
                if state_code != "not_installed" or (
                    plugin.manual_only or not plugin.auto_install
                ):
                    continue
            elif state_filter == "Installiert":
                if state_code != "installed":
                    continue
            elif state_filter == "Update verfügbar":
                if state_code != "update_available":
                    continue
            elif state_filter == "Manuelle Installation":
                if not plugin.manual_only:
                    continue
            elif state_filter == "Noch nicht installierbar":
                if plugin.manual_only or plugin.auto_install:
                    continue

            visible_plugins.append(plugin)

        self._filtered_mediahub_plugins = visible_plugins

        for plugin in visible_plugins:
            suffix = (
                " – manuelle Installation"
                if plugin.manual_only or not plugin.auto_install
                else ""
            )
            state_text = self._mediahub_state_text(plugin)
            item = QListWidgetItem(
                f"{plugin.name}  v{plugin.version}{suffix}\n"
                f"{state_text}"
            )
            item.setData(
                Qt.ItemDataRole.UserRole,
                plugin.plugin_id,
            )
            self.mediahub_list.addItem(item)

        self.mediahub_status.setText(
            f"{len(visible_plugins)} von "
            f"{len(self.mediahub_plugins)} Plugin(s) angezeigt."
        )

        if visible_plugins:
            self.mediahub_list.setCurrentRow(0)
        else:
            self.mediahub_details.setPlainText(
                "Keine Plugins passen zu den aktuellen Filtern."
            )

    def selected_mediahub_plugin(self) -> CatalogPlugin | None:
        row = self.mediahub_list.currentRow()
        plugins = getattr(
            self,
            "_filtered_mediahub_plugins",
            self.mediahub_plugins,
        )
        if 0 <= row < len(plugins):
            return plugins[row]
        return None

    def _show_mediahub_plugin(self, _row: int):
        plugin = self.selected_mediahub_plugin()

        if plugin is None:
            self.mediahub_details.clear()
            self.btn_mediahub_install.setEnabled(False)
            self.btn_mediahub_project.setEnabled(False)
            return

        state, installed_version = self._mediahub_plugin_state(plugin)
        self.btn_mediahub_project.setEnabled(bool(plugin.project_page))

        if state == "installed":
            self.btn_mediahub_install.setText("Bereits installiert")
            self.btn_mediahub_install.setEnabled(False)
        elif state == "update_available":
            self.btn_mediahub_install.setText(
                f"Auf v{plugin.version} aktualisieren"
            )
            self.btn_mediahub_install.setEnabled(
                plugin.auto_install and not plugin.manual_only
            )
        elif plugin.manual_only or not plugin.auto_install:
            self.btn_mediahub_install.setText(
                "Manuelle Installation anzeigen"
                if plugin.manual_only
                else "Noch nicht installierbar"
            )
            self.btn_mediahub_install.setEnabled(True)
        else:
            self.btn_mediahub_install.setText(
                "Herunterladen und installieren"
            )
            self.btn_mediahub_install.setEnabled(True)

        category = str(
            getattr(plugin, "category", "") or "Erweiterung"
        )
        minimum_version = str(
            getattr(plugin, "minimum_mediahub_version", "") or "-"
        )
        author = str(
            getattr(plugin, "author", "") or "MediaHub"
        )
        license_name = str(
            getattr(plugin, "license_name", "") or "-"
        )

        lines = [
            plugin.name,
            "",
            f"Status: {self._mediahub_state_text(plugin)}",
            f"Verfügbare Version: v{plugin.version}",
            (
                f"Installierte Version: v{installed_version}"
                if installed_version
                else "Installierte Version: -"
            ),
            f"Kategorie: {category}",
            f"Autor: {author}",
            f"Lizenz: {license_name}",
            f"Mindestens MediaHub: {minimum_version}",
            "",
            "Beschreibung:",
            plugin.description,
        ]

        note = str(plugin.manual_install_message or "").strip()
        if note:
            lines.extend(["", "Hinweis:", note])

        lines.extend(
            [
                "",
                "Projektseite:",
                plugin.project_page or "-",
            ]
        )

        self.mediahub_details.setPlainText("\n".join(lines))

    def install_selected_mediahub_plugin(self):
        plugin = self.selected_mediahub_plugin()
        if plugin is None:
            return

        if plugin.manual_only or not plugin.auto_install:
            self._show_manual_install(plugin)
            return

        try:
            package = self.catalog_service.download_plugin(plugin)
            ok, message = self.plugin_loader.install_mhplugin(package)
        except Exception as error:
            QMessageBox.warning(
                self,
                "Plugin installieren",
                str(error),
            )
            return

        dialog = (
            QMessageBox.information
            if ok
            else QMessageBox.warning
        )
        dialog(self, "Plugin installieren", message)

        if ok:
            try:
                self.plugin_loader.discover()
            except Exception:
                pass
            self.load_mediahub_catalog()

    def _show_manual_install(self, plugin: CatalogPlugin):
        box = QMessageBox(self)
        box.setWindowTitle(
            f"{plugin.name} manuell installieren"
        )
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(
            f"{plugin.name} kann nicht automatisch über den "
            "Plugin-Store installiert werden."
        )
        box.setInformativeText(
            plugin.manual_install_message
            or (
                "Bitte lade die aktuelle .mhplugin-Datei von der "
                "offiziellen GitHub-Seite herunter und installiere "
                "sie anschließend im Plugin Center."
            )
        )

        github_button = box.addButton(
            "GitHub-Seite öffnen",
            QMessageBox.ButtonRole.ActionRole,
        )
        box.addButton(
            "Schließen",
            QMessageBox.ButtonRole.RejectRole,
        )
        box.exec()

        if box.clickedButton() is github_button:
            webbrowser.open(plugin.project_page)

    def open_selected_project(self):
        plugin = self.selected_mediahub_plugin()
        if plugin and plugin.project_page:
            webbrowser.open(plugin.project_page)

    def open_selected_changelog(self):
        plugin = self.selected_mediahub_plugin()
        if plugin is None or not plugin.project_page:
            return

        url = plugin.project_page.rstrip("/") + "/blob/main/CHANGELOG.md"
        if "/tree/main/" in plugin.project_page:
            url = plugin.project_page.replace(
                "/tree/main/",
                "/blob/main/",
            ).rstrip("/") + "/CHANGELOG.md"

        webbrowser.open(url)

    def load_ai_catalog(self):
        try:
            plugins = self.ai_catalog_service.fetch_catalog()
        except Exception as error:
            self.ai_catalog_status.setText(
                f"AI-Plugin-Store: Katalog konnte nicht geladen werden: {error}"
            )
            return
        if not plugins:
            self.ai_catalog_status.setText(
                "AI-Plugin-Store: Noch keine AI-Plugins verfügbar. "
                "Sobald AI-Plugins veröffentlicht werden, erscheinen sie automatisch hier."
            )
            return
        self.ai_catalog_status.setText(
            f"AI-Plugin-Store: {len(plugins)} Plugin(s) verfügbar."
        )

    def install_ai_plugin_package(self):
        package_path, _ = QFileDialog.getOpenFileName(
            self,
            "AI-Plugin-Paket auswählen",
            str(Path.home()),
            "AI-Plugin-Pakete (*.mhaiplugin *.zip)",
        )
        if not package_path:
            return

        if not self._ensure_ai_node_ready_for_install():
            return

        service = self._ai_service()

        try:
            response = service.create_install_plan(package_path)
        except Exception as error:
            QMessageBox.warning(
                self,
                "AI-Plugin prüfen",
                str(error),
            )
            return

        plan_id = str(response.get("plan_id") or "")
        package = response.get("package", {})
        plan = response.get("plan", {})
        sha256 = str(
            package.get("sha256")
            if isinstance(package, dict)
            else ""
        )

        if not plan_id or not sha256:
            QMessageBox.warning(
                self,
                "AI-Plugin prüfen",
                "Der AI-Node hat keinen gültigen Installationsplan zurückgegeben.",
            )
            return

        if not self._confirm_plan_dialog(package, plan):
            try:
                service.cancel_install_plan(plan_id)
            except Exception:
                pass
            return

        actions = (
            plan.get("actions", [])
            if isinstance(plan, dict)
            else []
        )

        if actions:
            execute_answer = QMessageBox.question(
                self,
                "Voraussetzungen installieren",
                "Der Installationsplan enthält noch Voraussetzungen.\n\n"
                "MediaHub darf jetzt ausschließlich freigegebene "
                "Python-Pakete auf dem AI-Node installieren. "
                "Systemtools und weitere AI-Plugins werden nicht automatisch installiert.\n\n"
                "Freigegebene Schritte jetzt ausführen?",
            )
            if execute_answer != QMessageBox.StandardButton.Yes:
                try:
                    service.cancel_install_plan(plan_id)
                except Exception:
                    pass
                return

            try:
                response = service.execute_install_plan(plan_id)
            except Exception as error:
                QMessageBox.warning(
                    self,
                    "Voraussetzungen installieren",
                    str(error),
                )
                return

            plan = response.get("plan", {})
            if not self._plan_ready(plan):
                QMessageBox.warning(
                    self,
                    "AI-Plugin noch nicht installierbar",
                    self._format_pending_plan(plan),
                )
                return

        try:
            result = service.confirm_install_plan(
                plan_id,
                sha256,
            )
        except Exception as error:
            QMessageBox.warning(
                self,
                "AI-Plugin installieren",
                str(error),
            )
            return

        plugin = result.get("plugin", {})
        name = (
            str(plugin.get("name") or plugin.get("id") or "AI-Plugin")
            if isinstance(plugin, dict)
            else "AI-Plugin"
        )
        QMessageBox.information(
            self,
            "AI-Plugin installieren",
            f"{name} wurde erfolgreich auf dem AI-Node installiert.",
        )
        self.load_ai_plugins()

    def _confirm_plan_dialog(
        self,
        package: object,
        plan: object,
    ) -> bool:
        package_data = package if isinstance(package, dict) else {}
        plan_data = plan if isinstance(plan, dict) else {}

        lines = [
            f"Name: {package_data.get('name', 'unbekannt')}",
            f"Plugin-ID: {package_data.get('plugin_id', 'unbekannt')}",
            f"Version: {package_data.get('version', 'unbekannt')}",
            f"Typ: {package_data.get('type', 'unbekannt')}",
            f"SHA-256: {package_data.get('sha256', 'unbekannt')}",
            "",
            f"Lizenz vorhanden: {'Ja' if plan_data.get('license_present') else 'Nein'}",
        ]

        warnings = plan_data.get("warnings", [])
        if isinstance(warnings, list) and warnings:
            lines.extend(["", "Warnungen:"])
            lines.extend(f"- {warning}" for warning in warnings)

        actions = plan_data.get("actions", [])
        if isinstance(actions, list) and actions:
            lines.extend(["", "Noch erforderliche Schritte:"])
            for action in actions:
                if not isinstance(action, dict):
                    continue
                lines.append(
                    f"- {action.get('type', 'unbekannt')}: "
                    f"{action.get('name', 'unbekannt')} "
                    f"({action.get('reason', 'keine Begründung')})"
                )
        else:
            lines.extend(["", "Keine weiteren Voraussetzungen erforderlich."])

        answer = QMessageBox.question(
            self,
            "AI-Plugin-Installationsplan bestätigen",
            "\n".join(lines)
            + "\n\nSoll dieser Installationsplan verwendet werden?",
        )
        return answer == QMessageBox.StandardButton.Yes

    @staticmethod
    def _plan_ready(plan: object) -> bool:
        if not isinstance(plan, dict):
            return False
        actions = plan.get("actions", [])
        return bool(plan.get("ready_without_changes", False)) or not actions

    @staticmethod
    def _format_pending_plan(plan: object) -> str:
        if not isinstance(plan, dict):
            return "Der aktualisierte Installationsplan ist ungültig."

        actions = plan.get("actions", [])
        lines = [
            "Es sind noch Voraussetzungen offen, die MediaHub "
            "nicht automatisch installieren darf:",
            "",
        ]
        if isinstance(actions, list):
            for action in actions:
                if isinstance(action, dict):
                    lines.append(
                        f"- {action.get('type', 'unbekannt')}: "
                        f"{action.get('name', 'unbekannt')} "
                        f"({action.get('reason', 'keine Begründung')})"
                    )
        return "\n".join(lines)

    def _ensure_ai_node_ready_for_install(self) -> bool:
        """Prüft den AI-Node und installiert oder repariert ihn bei Bedarf."""

        settings = self.settings_service.load()
        if not isinstance(settings, dict):
            settings = {}

        ai = settings.get("ai")
        if not isinstance(ai, dict):
            ai = {}

        try:
            service = AINodeService.from_settings(
                settings,
                timeout=4.0,
            )
            health = service.health()
            if health.online:
                service.list_plugins()
                return True
        except Exception:
            pass

        host = str(ai.get("node_host") or "").strip()
        if not host:
            host, accepted = QInputDialog.getText(
                self,
                "AI-Node einrichten",
                "IP-Adresse oder Hostname des Raspberry Pi:",
            )
            host = str(host).strip()
            if not accepted or not host:
                return False

        username = str(
            ai.get("ssh_username") or "mediahub"
        ).strip() or "mediahub"

        username, accepted = QInputDialog.getText(
            self,
            "AI-Node einrichten",
            "SSH-Benutzer:",
            QLineEdit.EchoMode.Normal,
            username,
        )
        username = str(username).strip()
        if not accepted or not username:
            return False

        password, accepted = QInputDialog.getText(
            self,
            "AI-Node einrichten",
            "SSH-Passwort (wird nicht gespeichert):",
            QLineEdit.EchoMode.Password,
        )
        if not accepted or not password:
            return False

        ssh_port = int(ai.get("ssh_port") or 22)
        api_port = int(ai.get("api_port") or 8765)
        install_path = str(
            ai.get("install_path")
            or "/opt/mediahub/ai-node"
        ).strip()

        answer = QMessageBox.question(
            self,
            "AI-Node automatisch einrichten",
            "Der AI-Node ist über die REST-API nicht erreichbar.\n\n"
            "MediaHub prüft den Raspberry Pi jetzt über SSH und wird "
            "den AI-Node bei Bedarf installieren oder reparieren.\n\n"
            "Fortfahren?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False

        progress = QProgressDialog(
            "Der MediaHub-AI-Node wird auf dem Raspberry Pi eingerichtet.\n\n"
            "Die erste Installation kann je nach Internetverbindung und "
            "Geschwindigkeit des Raspberry Pi mehrere Minuten dauern.\n\n"
            "Bitte MediaHub währenddessen nicht schließen.",
            "",
            0,
            0,
            self,
        )
        progress.setWindowTitle("MediaHub-AI-Node wird eingerichtet")
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.show()
        QApplication.processEvents()

        try:
            progress.setLabelText(
                "SSH-Verbindung hergestellt.\n"
                "AI-Node wird geprüft, installiert oder repariert ...\n\n"
                "Dieser Vorgang kann mehrere Minuten dauern."
            )
            QApplication.processEvents()

            provisioner = AINodeProvisioningService(
                host=host,
                ssh_port=ssh_port,
                username=username,
                password=password,
                project_dir=install_path,
                timeout=15.0,
            )
            result = provisioner.ensure_ready()

            progress.setLabelText(
                "AI-Node wurde eingerichtet.\n"
                "API-Token und Verbindung werden geprüft ..."
            )
            QApplication.processEvents()
        except AINodeProvisioningError as error:
            progress.close()
            QMessageBox.warning(
                self,
                "AI-Node einrichten",
                str(error),
            )
            return False
        except Exception as error:
            progress.close()
            QMessageBox.warning(
                self,
                "AI-Node einrichten",
                "Die automatische Einrichtung ist fehlgeschlagen:\n"
                f"{error}",
            )
            return False

        token = str(result.api_token or "").strip()
        if not token:
            progress.close()
            QMessageBox.warning(
                self,
                "AI-Node einrichten",
                "Der AI-Node wurde eingerichtet, aber MediaHub hat "
                "kein API-Token erhalten.",
            )
            return False

        ai.update(
            {
                "node_enabled": True,
                "node_host": host,
                "api_port": api_port,
                "api_token": token,
                "ssh_port": ssh_port,
                "ssh_username": username,
                "install_path": install_path,
            }
        )
        settings["ai"] = ai
        self.settings_service.save(settings)

        try:
            service = AINodeService.from_settings(
                settings,
                timeout=12.0,
            )
            health = service.health()
            if not health.online:
                raise RuntimeError(health.message)
            service.list_plugins()
        except Exception as error:
            progress.close()
            QMessageBox.warning(
                self,
                "AI-Node einrichten",
                "Der AI-Node wurde installiert, aber die abschließende "
                f"Verbindungsprüfung ist fehlgeschlagen:\n{error}",
            )
            return False

        progress.close()

        QMessageBox.information(
            self,
            "AI-Node einrichten",
            "Der AI-Node ist installiert, verbunden und für die "
            "Plugin-Installation bereit.",
        )
        return True

    def _ai_service(self) -> AINodeService:
        return AINodeService.from_settings(
            self.settings_service.load(),
            timeout=8.0,
        )

    def selected_ai_plugin(self) -> dict | None:
        row = self.ai_list.currentRow()
        plugins = getattr(
            self,
            "_filtered_ai_plugins",
            self.ai_plugins,
        )
        if 0 <= row < len(plugins):
            return plugins[row]
        return None

    def _selected_ai_plugin_id(self) -> str:
        plugin = self.selected_ai_plugin()
        if plugin is None:
            return ""
        return str(
            plugin.get("id")
            or plugin.get("plugin_id")
            or ""
        ).strip()

    def _set_ai_action_buttons(self, enabled: bool):
        self.btn_ai_enable.setEnabled(enabled)
        self.btn_ai_disable.setEnabled(enabled)
        self.btn_ai_remove.setEnabled(enabled)

    def enable_selected_ai_plugin(self):
        plugin_id = self._selected_ai_plugin_id()
        if not plugin_id:
            return

        try:
            self._ai_service().enable_plugin(plugin_id)
        except Exception as error:
            QMessageBox.warning(
                self,
                "AI-Plugin aktivieren",
                str(error),
            )
            return

        QMessageBox.information(
            self,
            "AI-Plugin aktivieren",
            f"AI-Plugin aktiviert: {plugin_id}",
        )
        self.load_ai_plugins()

    def disable_selected_ai_plugin(self):
        plugin_id = self._selected_ai_plugin_id()
        if not plugin_id:
            return

        try:
            self._ai_service().disable_plugin(plugin_id)
        except Exception as error:
            QMessageBox.warning(
                self,
                "AI-Plugin deaktivieren",
                str(error),
            )
            return

        QMessageBox.information(
            self,
            "AI-Plugin deaktivieren",
            f"AI-Plugin deaktiviert: {plugin_id}",
        )
        self.load_ai_plugins()

    def remove_selected_ai_plugin(self):
        plugin = self.selected_ai_plugin()
        plugin_id = self._selected_ai_plugin_id()
        if plugin is None or not plugin_id:
            return

        name = str(plugin.get("name") or plugin_id)
        answer = QMessageBox.question(
            self,
            "AI-Plugin entfernen",
            f"{name} wirklich vom Raspberry-Pi-AI-Node entfernen?\n\n"
            "Vor dem Entfernen wird auf dem Pi automatisch eine Sicherung angelegt.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            result = self._ai_service().remove_plugin(
                plugin_id,
                create_backup=True,
            )
        except Exception as error:
            QMessageBox.warning(
                self,
                "AI-Plugin entfernen",
                str(error),
            )
            return

        backup_created = bool(result.get("backup_created", False))
        message = f"AI-Plugin entfernt: {name}"
        if backup_created:
            message += "\nEine Sicherung wurde auf dem Pi angelegt."

        QMessageBox.information(
            self,
            "AI-Plugin entfernen",
            message,
        )
        self.load_ai_plugins()

    def load_ai_plugins(self):
        self.ai_list.clear()
        self.ai_details.clear()
        self._set_ai_action_buttons(False)

        settings = self.settings_service.load()
        service = AINodeService.from_settings(
            settings,
            timeout=5.0,
        )
        health = service.health()

        if not health.online:
            self.ai_plugins = []
            self._filtered_ai_plugins = []
            self.ai_status.setText(
                "AI-Node offline oder nicht eingerichtet: "
                f"{health.message}"
            )
            self.ai_details.setPlainText(
                "Prüfe die Verbindung unter "
                "Globale Einstellungen → KI-Verbindungen."
            )
            return

        self.ai_status.setText(
            f"AI-Node online – Status: {health.status}, "
            f"Version: {health.version}"
        )

        try:
            self.ai_plugins = service.list_plugins()
        except Exception as error:
            self.ai_plugins = []
            self._filtered_ai_plugins = []
            self.ai_details.setPlainText(
                "AI-Plugin-Liste konnte nicht geladen werden:\n"
                f"{error}"
            )
            return

        self.apply_ai_filters()

    def apply_ai_filters(self):
        search = self.ai_search.text().strip().lower()
        state_filter = self.ai_state_filter.currentText()

        self.ai_list.clear()
        self.ai_details.clear()
        self._set_ai_action_buttons(False)

        visible_plugins = []

        for plugin in self.ai_plugins:
            plugin_id = str(
                plugin.get("id")
                or plugin.get("plugin_id")
                or "unbekannt"
            )
            name = str(plugin.get("name") or plugin_id)
            version = str(plugin.get("version") or "unbekannt")
            plugin_type = str(
                plugin.get("type")
                or plugin.get("plugin_type")
                or "unbekannt"
            )
            enabled = bool(plugin.get("enabled", False))
            loaded = bool(plugin.get("loaded", False))
            error = plugin.get("error")

            searchable = " ".join(
                [
                    plugin_id,
                    name,
                    version,
                    plugin_type,
                    str(error or ""),
                ]
            ).lower()

            if search and search not in searchable:
                continue

            if state_filter == "Aktiviert" and not enabled:
                continue
            if state_filter == "Deaktiviert" and enabled:
                continue
            if state_filter == "Geladen" and not loaded:
                continue
            if state_filter == "Nicht geladen" and loaded:
                continue
            if state_filter == "Fehler" and not error:
                continue

            visible_plugins.append(plugin)

        self._filtered_ai_plugins = visible_plugins

        for plugin in visible_plugins:
            plugin_id = str(
                plugin.get("id")
                or plugin.get("plugin_id")
                or "unbekannt"
            )
            name = str(plugin.get("name") or plugin_id)
            version = str(plugin.get("version") or "unbekannt")
            enabled = bool(plugin.get("enabled", False))
            loaded = bool(plugin.get("loaded", False))
            error = plugin.get("error")

            states = [
                "aktiviert" if enabled else "deaktiviert",
                "geladen" if loaded else "nicht geladen",
            ]
            if error:
                states.append("Fehler")

            item = QListWidgetItem(
                f"{name}  v{version} – {', '.join(states)}"
            )
            item.setData(
                Qt.ItemDataRole.UserRole,
                plugin_id,
            )
            self.ai_list.addItem(item)

        total = len(self.ai_plugins)
        visible = len(visible_plugins)
        current_status = self.ai_status.text().split(" | ")[0]
        self.ai_status.setText(
            f"{current_status} | {visible} von {total} AI-Plugin(s) angezeigt"
        )

        if visible_plugins:
            self.ai_list.setCurrentRow(0)
        elif total:
            self.ai_details.setPlainText(
                "Keine AI-Plugins passen zu den aktuellen Filtern."
            )
        else:
            self.ai_details.setPlainText(
                "Der AI-Node ist online, aber es sind noch "
                "keine AI-Plugins installiert."
            )

    def _show_ai_plugin(self, row: int):
        plugins = getattr(
            self,
            "_filtered_ai_plugins",
            self.ai_plugins,
        )
        if not 0 <= row < len(plugins):
            self.ai_details.clear()
            self._set_ai_action_buttons(False)
            return

        plugin = plugins[row]
        self._set_ai_action_buttons(True)
        enabled = bool(plugin.get("enabled", False))
        self.btn_ai_enable.setEnabled(not enabled)
        self.btn_ai_disable.setEnabled(enabled)
        plugin_id = str(
            plugin.get("id")
            or plugin.get("plugin_id")
            or "unbekannt"
        )
        name = str(plugin.get("name") or plugin_id)
        version = str(plugin.get("version") or "unbekannt")
        plugin_type = str(
            plugin.get("type")
            or plugin.get("plugin_type")
            or "unbekannt"
        )
        enabled = bool(plugin.get("enabled", False))
        loaded = bool(plugin.get("loaded", False))

        lines = [
            name,
            f"Plugin-ID: {plugin_id}",
            f"Version: {version}",
            f"Typ: {plugin_type}",
            f"Aktiviert: {'Ja' if enabled else 'Nein'}",
            f"Geladen: {'Ja' if loaded else 'Nein'}",
        ]

        error = plugin.get("error")
        if error:
            lines.extend(["", f"Fehler: {error}"])

        self.ai_details.setPlainText("\n".join(lines))
