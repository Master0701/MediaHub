from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class ToolCard(QFrame):
    """Kompakte Statuskarte für ein MediaHub- oder Plugin-Werkzeug."""

    def __init__(
        self,
        tool: dict,
        install_callback=None,
        update_callback=None,
        install_update_callback=None,
        reinstall_callback=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("toolCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(310)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        title_row = QHBoxLayout()
        status_symbol = "✓" if tool["installed"] else "✗"
        title = QLabel(f"{status_symbol}  {tool['display_name']}")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        title_row.addWidget(title)
        title_row.addStretch(1)

        category_text = "MediaHub" if tool["category"] == "mediahub" else "Plugin"
        category = QLabel(category_text)
        category.setAlignment(Qt.AlignmentFlag.AlignCenter)
        category.setStyleSheet(
            "padding: 2px 7px; border: 1px solid palette(mid); border-radius: 7px;"
        )
        title_row.addWidget(category)
        layout.addLayout(title_row)

        state = "Installiert" if tool["installed"] else "Nicht installiert"
        layout.addWidget(self._line("Status", state))
        layout.addWidget(self._line("Version", str(tool.get("version") or "unbekannt")))
        layout.addWidget(self._line("Neueste Version", str(tool.get("latest_version") or "noch nicht geprüft")))
        layout.addWidget(self._line("Update", str(tool.get("update_status") or "Noch nicht geprüft")))
        layout.addWidget(self._line("Quelle", str(tool.get("installation_source") or "unbekannt")))
        layout.addWidget(self._line("Lizenz", str(tool.get("license") or "unbekannt")))

        used_by = list(tool.get("used_by") or [])
        usage = ", ".join(used_by) if used_by else "Derzeit nicht verwendet"
        layout.addWidget(self._line("Benutzt von", usage))

        optional_by = list(tool.get("optional_by") or [])
        if optional_by:
            layout.addWidget(self._line("Optional für", ", ".join(optional_by)))

        path_label = QLabel(str(tool.get("path") or ""))
        path_label.setWordWrap(True)
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path_label.setToolTip(str(tool.get("path") or ""))
        layout.addWidget(self._line("Pfad", ""))
        layout.addWidget(path_label)

        action_row = QHBoxLayout()
        if not tool.get("installed") and tool.get("can_install") and callable(install_callback):
            install_button = QPushButton("Installieren")
            install_button.clicked.connect(lambda: install_callback(str(tool.get("tool_id") or "")))
            action_row.addWidget(install_button)
        elif tool.get("installed"):
            tool_id = str(tool.get("tool_id") or "")
            update_button = QPushButton("Update prüfen")
            update_button.setEnabled(callable(update_callback))
            if callable(update_callback):
                update_button.clicked.connect(lambda: update_callback(tool_id))
            action_row.addWidget(update_button)

            install_update_button = QPushButton("Aktualisieren")
            safe_update = bool(tool.get("safe_update_supported"))
            update_available = tool.get("update_available") is True
            install_update_button.setEnabled(
                safe_update and update_available and callable(install_update_callback)
            )
            if safe_update and not update_available:
                install_update_button.setToolTip(
                    "Zuerst die Update-Prüfung ausführen. Der Knopf wird bei einem verfügbaren Update aktiviert."
                )
            elif not safe_update:
                install_update_button.setToolTip(
                    "Der sichere Updater für dieses Werkzeug folgt in einem späteren Schritt."
                )
            if callable(install_update_callback):
                install_update_button.clicked.connect(lambda: install_update_callback(tool_id))
            action_row.addWidget(install_update_button)

            reinstall_button = QPushButton("Neu installieren")
            reinstall_button.setEnabled(safe_update and callable(reinstall_callback))
            if not safe_update:
                reinstall_button.setToolTip(
                    "Die sichere Neuinstallation für dieses Werkzeug folgt in einem späteren Schritt."
                )
            if callable(reinstall_callback):
                reinstall_button.clicked.connect(lambda: reinstall_callback(tool_id))
            action_row.addWidget(reinstall_button)

        if action_row.count():
            action_row.addStretch(1)
            layout.addLayout(action_row)

    @staticmethod
    def _line(label: str, value: str) -> QLabel:
        widget = QLabel(f"<b>{label}:</b> {value}")
        widget.setWordWrap(True)
        widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return widget


class ToolAssistant(QDialog):
    """Geführte Gesamtprüfung für fehlende Tools und sichere Updates."""

    def __init__(self, tool_service, parent=None):
        super().__init__(parent)
        self.tool_service = tool_service
        self.setWindowTitle("MediaHub Tool-Assistent")
        self.resize(700, 520)
        self.setMinimumSize(620, 440)

        layout = QVBoxLayout(self)
        heading = QLabel("🛠 MediaHub Tool-Assistent")
        heading.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(heading)

        info = QLabel(
            "Der Assistent prüft die komplette Tool-Umgebung, installiert fehlende "
            "Plugin-Pflichttools und aktualisiert sicher unterstützte MediaHub-Tools."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-weight: 600; padding: 8px;")
        layout.addWidget(self.status_label)

        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.details.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.details)
        layout.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        self.btn_check = QPushButton("Alles prüfen")
        self.btn_install = QPushButton("Fehlende installieren")
        self.btn_update = QPushButton("Sichere Updates installieren")
        self.btn_close = QPushButton("Schließen")
        self.btn_check.clicked.connect(self.check_all)
        self.btn_install.clicked.connect(self.install_missing)
        self.btn_update.clicked.connect(self.install_updates)
        self.btn_close.clicked.connect(self.close)
        buttons.addWidget(self.btn_check)
        buttons.addWidget(self.btn_install)
        buttons.addWidget(self.btn_update)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_close)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        data = self.tool_service.get_tool_assistant_status(include_versions=True)
        summary = data.get("summary") or {}
        self.status_label.setText(
            f"Installiert: {summary.get('installed', 0)}  |  "
            f"Fehlend: {summary.get('missing', 0)}  |  "
            f"Updates verfügbar: {data.get('updates_available', 0)}  |  "
            f"Sicher aktualisierbar: {data.get('safe_updates_available', 0)}"
        )
        lines = []
        for tool in data.get("tools") or []:
            symbol = "✓" if tool.get("installed") else "✗"
            update = str(tool.get("update_status") or "Noch nicht geprüft")
            usage = ", ".join(tool.get("used_by") or []) or "nicht verwendet"
            lines.append(
                f"{symbol} {tool.get('display_name')} — {tool.get('version', 'unbekannt')}"
                f"\n   Update: {update} | Benutzt von: {usage}"
            )
        self.details.setText("\n\n".join(lines))
        self.btn_install.setEnabled(bool(data.get("missing_required_tools")))
        self.btn_update.setEnabled(bool(data.get("safe_update_tools")))

    def check_all(self) -> None:
        self.setEnabled(False)
        try:
            results = self.tool_service.check_all_tool_updates()
            available = [item for item in results if item.get("update_available") is True]
            QMessageBox.information(
                self,
                "Tool-Assistent",
                f"{len(results)} installierte Tools wurden geprüft.\n"
                f"{len(available)} Update(s) wurden gefunden.",
            )
        except Exception as error:
            QMessageBox.critical(self, "Tool-Assistent", f"Prüfung fehlgeschlagen:\n\n{error}")
        finally:
            self.setEnabled(True)
            self.refresh()

    def install_missing(self) -> None:
        data = self.tool_service.get_tool_assistant_status(include_versions=False)
        missing = list(data.get("missing_required_tools") or [])
        if not missing:
            QMessageBox.information(
                self,
                "Tool-Assistent",
                "Alle Pflichttools von MediaHub und den aktivierten Plugins sind vorhanden.",
            )
            return

        names = [str(item.get("display_name") or item.get("tool_id") or "Tool") for item in missing]
        answer = QMessageBox.question(
            self,
            "Fehlende Pflichttools",
            "Folgende fehlende Pflichttools werden eingerichtet:\n\n"
            + "\n".join(f"• {name}" for name in names)
            + "\n\nMediaHub-Tools werden aus den hinterlegten offiziellen Quellen geladen. "
              "Plugin-Pflichttools werden über WinGet installiert. Fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.setEnabled(False)
        try:
            results = self.tool_service.install_missing_required_tools()
            remaining = self.tool_service.get_tool_assistant_status(include_versions=False).get(
                "missing_required_tools", []
            )
            if remaining:
                remaining_names = "\n".join(
                    f"• {item.get('display_name') or item.get('tool_id')}" for item in remaining
                )
                QMessageBox.warning(
                    self,
                    "Tool-Assistent",
                    f"{len(results)} Pflichttool(s) wurden eingerichtet.\n\n"
                    "Folgende Pflichttools fehlen weiterhin:\n"
                    f"{remaining_names}",
                )
            else:
                QMessageBox.information(
                    self,
                    "Tool-Assistent",
                    f"{len(results)} Pflichttool(s) wurden erfolgreich eingerichtet.",
                )
        except Exception as error:
            QMessageBox.critical(self, "Tool-Assistent", f"Installation fehlgeschlagen:\n\n{error}")
        finally:
            self.setEnabled(True)
            self.refresh()

    def install_updates(self) -> None:
        data = self.tool_service.get_tool_assistant_status(include_versions=False)
        count = int(data.get("safe_updates_available", 0))
        if count <= 0:
            QMessageBox.information(self, "Tool-Assistent", "Es sind keine sicheren Updates vorgemerkt.")
            return
        answer = QMessageBox.question(
            self,
            "Sichere Updates",
            f"{count} sicher unterstützte(s) Tool(s) werden nacheinander aktualisiert. Fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.setEnabled(False)
        try:
            results = self.tool_service.update_all_available_safe_tools()
            success = [item for item in results if item.get("success")]
            failed = [item for item in results if not item.get("success")]
            text = f"Erfolgreich aktualisiert: {len(success)}"
            if failed:
                text += f"\nFehlgeschlagen: {len(failed)}\n\n" + "\n".join(
                    f"• {item.get('display_name')}: {item.get('error')}" for item in failed
                )
            QMessageBox.information(self, "Tool-Assistent", text)
        except Exception as error:
            QMessageBox.critical(self, "Tool-Assistent", f"Sammelupdate fehlgeschlagen:\n\n{error}")
        finally:
            self.setEnabled(True)
            self.refresh()


class ToolCenter(QDialog):
    CATEGORY_FILTERS = {
        "Alle Tools": "all",
        "MediaHub": "mediahub",
        "Plugins": "plugin",
    }
    STATE_FILTERS = {
        "Alle Status": "all",
        "Installiert": "installed",
        "Fehlend": "missing",
        "Benutzt": "used",
        "Nicht verwendet": "unused",
        "Erforderlich": "required",
        "Optional": "optional",
    }

    def __init__(self, tool_service, parent=None):
        super().__init__(parent)
        self.tool_service = tool_service
        self._cards: list[ToolCard] = []
        self._refresh_pending = False
        self.tool_service.add_change_listener(self._schedule_refresh)

        self.setWindowTitle("Tool-Center")
        self.resize(920, 650)
        self.setMinimumSize(760, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        heading = QLabel("🧰 Tool-Manager")
        heading.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(heading)

        info = QLabel(
            "Übersicht über die Werkzeuge des Hauptprogramms und die von Plugins "
            "angemeldeten Pflicht- und optionalen Werkzeuge."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Bereich:"))
        self.category_filter = QComboBox()
        self.category_filter.addItems(self.CATEGORY_FILTERS)
        filter_row.addWidget(self.category_filter)

        filter_row.addWidget(QLabel("Status:"))
        self.state_filter = QComboBox()
        self.state_filter.addItems(self.STATE_FILTERS)
        filter_row.addWidget(self.state_filter)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        self.category_filter.currentTextChanged.connect(self.refresh)
        self.state_filter.currentTextChanged.connect(self.refresh)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.StyledPanel)
        self.cards_host = QWidget()
        self.cards_layout = QGridLayout(self.cards_host)
        self.cards_layout.setContentsMargins(10, 10, 10, 10)
        self.cards_layout.setHorizontalSpacing(10)
        self.cards_layout.setVerticalSpacing(10)
        self.cards_layout.setColumnStretch(0, 1)
        self.cards_layout.setColumnStretch(1, 1)
        self.scroll.setWidget(self.cards_host)
        layout.addWidget(self.scroll, 1)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("font-weight: 600; padding: 6px;")
        layout.addWidget(self.summary)

        buttons = QHBoxLayout()
        self.btn_check = QPushButton("Tools prüfen")
        self.btn_check_updates = QPushButton("Alle Updates prüfen")
        self.btn_assistant = QPushButton("Tool-Assistent")
        self.btn_open = QPushButton("Tools-Ordner öffnen")
        self.btn_redownload = QPushButton("MediaHub-Tools neu herunterladen")
        self.btn_install_plugin_tools = QPushButton("Fehlende Plugin-Pflichttools installieren")
        self.btn_close = QPushButton("Schließen")

        self.btn_check.clicked.connect(self.refresh)
        self.btn_check_updates.clicked.connect(self.check_all_updates)
        self.btn_assistant.clicked.connect(self.open_tool_assistant)
        self.btn_open.clicked.connect(self.tool_service.open_tools_folder)
        self.btn_redownload.clicked.connect(self.redownload_tools)
        self.btn_install_plugin_tools.clicked.connect(self.install_required_plugin_tools)
        self.btn_close.clicked.connect(self.close)

        buttons.addWidget(self.btn_check)
        buttons.addWidget(self.btn_check_updates)
        buttons.addWidget(self.btn_assistant)
        buttons.addWidget(self.btn_open)
        buttons.addWidget(self.btn_redownload)
        buttons.addWidget(self.btn_install_plugin_tools)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_close)
        layout.addLayout(buttons)

        self.refresh()


    def _schedule_refresh(self) -> None:
        """Aktualisiert den geöffneten Dialog sicher im Qt-Ereigniszyklus."""

        if self._refresh_pending:
            return
        self._refresh_pending = True
        QTimer.singleShot(0, self._refresh_after_change)

    def _refresh_after_change(self) -> None:
        self._refresh_pending = False
        if self.isVisible():
            self.refresh()

    def closeEvent(self, event) -> None:
        self.tool_service.remove_change_listener(self._schedule_refresh)
        super().closeEvent(event)

    def _clear_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards.clear()

    def refresh(self) -> None:
        category = self.CATEGORY_FILTERS.get(self.category_filter.currentText(), "all")
        state = self.STATE_FILTERS.get(self.state_filter.currentText(), "all")

        try:
            data = self.tool_service.get_tool_manager_data(
                include_versions=True,
                category=category,
                state=state,
            )
        except Exception as error:
            QMessageBox.critical(self, "Tool-Manager", f"Tool-Status konnte nicht gelesen werden:\n\n{error}")
            return

        self._clear_cards()
        tools = list(data.get("tools") or [])
        for index, tool in enumerate(tools):
            card = ToolCard(
                tool,
                install_callback=self.install_single_plugin_tool,
                update_callback=self.check_single_update,
                install_update_callback=self.install_single_update,
                reinstall_callback=self.reinstall_single_tool,
                parent=self.cards_host,
            )
            self._cards.append(card)
            self.cards_layout.addWidget(card, index // 2, index % 2)

        if not tools:
            empty = QLabel("Für diese Filter wurden keine Tools gefunden.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_layout.addWidget(empty, 0, 0, 1, 2)

        summary = data.get("summary") or {}
        filtered = data.get("filtered_summary") or {}
        self.summary.setText(
            "Gesamt: {total}  |  Installiert: {installed}  |  Fehlend: {missing}  |  "
            "Benutzt: {used}  |  Nicht verwendet: {unused}    "
            "— Angezeigt: {shown}".format(
                total=summary.get("total", 0),
                installed=summary.get("installed", 0),
                missing=summary.get("missing", 0),
                used=summary.get("used", 0),
                unused=summary.get("unused", 0),
                shown=filtered.get("total", len(tools)),
            )
        )



    def open_tool_assistant(self) -> None:
        dialog = ToolAssistant(self.tool_service, self)
        dialog.exec()
        self.refresh()


    def check_single_update(self, tool_id: str) -> None:
        self.setEnabled(False)
        try:
            result = self.tool_service.check_tool_update(tool_id)
            name = str(result.get("display_name") or tool_id)
            QMessageBox.information(
                self,
                "Update-Prüfung",
                f"{name}\n\nInstalliert: {result.get('version', 'unbekannt')}\n"
                f"Neueste Version: {result.get('latest_version', 'unbekannt')}\n"
                f"Status: {result.get('update_status', 'unbekannt')}",
            )
        except Exception as error:
            QMessageBox.critical(self, "Update-Prüfung", f"Update-Prüfung fehlgeschlagen:\n\n{error}")
        finally:
            self.setEnabled(True)
            self.refresh()

    def check_all_updates(self) -> None:
        self.setEnabled(False)
        try:
            results = self.tool_service.check_all_tool_updates()
            available = [item for item in results if item.get("update_available") is True]
            failed = [item for item in results if str(item.get("update_status", "")).startswith("Fehler:")]
            lines = [f"Geprüfte Tools: {len(results)}", f"Updates verfügbar: {len(available)}"]
            if available:
                lines.append("\n" + "\n".join(f"• {item['display_name']}: {item['latest_version']}" for item in available))
            if failed:
                lines.append(f"\nNicht erfolgreich prüfbar: {len(failed)}")
            QMessageBox.information(self, "Alle Updates prüfen", "\n".join(lines))
        except Exception as error:
            QMessageBox.critical(self, "Alle Updates prüfen", f"Update-Prüfung fehlgeschlagen:\n\n{error}")
        finally:
            self.setEnabled(True)
            self.refresh()

    def install_single_update(self, tool_id: str) -> None:
        status = self.tool_service.find_tool_status(tool_id, include_version=True) or {}
        name = str(status.get("display_name") or tool_id)
        if not status.get("safe_update_supported"):
            QMessageBox.information(
                self,
                "Werkzeug aktualisieren",
                f"Für {name} ist der sichere automatische Updater noch nicht freigeschaltet.",
            )
            return

        check = self.tool_service.check_tool_update(tool_id)
        if check.get("update_available") is not True:
            QMessageBox.information(
                self,
                "Werkzeug aktualisieren",
                f"Für {name} ist derzeit kein neueres Update verfügbar.\n\n"
                f"Installiert: {check.get('version', 'unbekannt')}\n"
                f"Neueste Version: {check.get('latest_version', 'unbekannt')}",
            )
            self.refresh()
            return

        answer = QMessageBox.question(
            self,
            "Werkzeug aktualisieren",
            f"{name} wird sicher aktualisiert.\n\n"
            f"Installiert: {check.get('version', 'unbekannt')}\n"
            f"Neueste Version: {check.get('latest_version', 'unbekannt')}\n\n"
            "Die vorhandene Datei wird gesichert und bei einem Fehler automatisch wiederhergestellt. Fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._run_safe_mediahub_update(tool_id, name, "aktualisiert")

    def reinstall_single_tool(self, tool_id: str) -> None:
        status = self.tool_service.find_tool_status(tool_id, include_version=True) or {}
        name = str(status.get("display_name") or tool_id)
        if not status.get("safe_update_supported"):
            QMessageBox.information(
                self,
                "Werkzeug neu installieren",
                f"Für {name} ist die sichere Neuinstallation noch nicht freigeschaltet.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Werkzeug neu installieren",
            f"{name} wird vollständig neu heruntergeladen und sicher ersetzt.\n\n"
            "Die vorhandene Datei wird gesichert und bei einem Fehler automatisch wiederhergestellt. Fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._run_safe_mediahub_update(tool_id, name, "neu installiert")

    def _run_safe_mediahub_update(self, tool_id: str, name: str, success_text: str) -> None:
        self.setEnabled(False)
        try:
            result = self.tool_service.update_mediahub_tool(tool_id)
            version = str(result.get("version") or "unbekannt")
            QMessageBox.information(
                self,
                "Werkzeugverwaltung",
                f"{name} wurde erfolgreich {success_text}.\n\nVersion: {version}",
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Werkzeugverwaltung",
                f"{name} konnte nicht {success_text} werden.\n\n"
                "Die vorherige Version wurde, soweit vorhanden, automatisch wiederhergestellt.\n\n"
                f"{error}",
            )
        finally:
            self.setEnabled(True)
            self.refresh()

    def install_single_plugin_tool(self, tool_id: str) -> None:
        status = self.tool_service.find_tool_status(tool_id, include_version=False) or {}
        name = str(status.get("display_name") or tool_id)
        answer = QMessageBox.question(
            self,
            "Plugin-Werkzeug installieren",
            f"{name} wird portabel in MediaHub/tools installiert.\n\nFortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.setEnabled(False)
        try:
            self.tool_service.install_plugin_tool(tool_id)
            QMessageBox.information(self, "Plugin-Werkzeug", f"{name} wurde erfolgreich installiert.")
        except Exception as error:
            QMessageBox.critical(self, "Plugin-Werkzeug", f"Installation fehlgeschlagen:\n\n{error}")
        finally:
            self.setEnabled(True)
            self.refresh()

    def install_required_plugin_tools(self) -> None:
        missing = self.tool_service.missing_required_plugin_tools()
        if not missing:
            QMessageBox.information(
                self,
                "Plugin-Werkzeuge",
                "Alle Pflichttools der aktivierten Plugins sind bereits vorhanden.",
            )
            return

        names = []
        for tool_id in missing:
            status = self.tool_service.find_tool_status(tool_id, include_version=False) or {}
            names.append(str(status.get("display_name") or tool_id))

        answer = QMessageBox.question(
            self,
            "Plugin-Pflichttools installieren",
            "Folgende fehlende Pflichttools werden über Windows Package Manager installiert:\n\n"
            + "\n".join(f"• {name}" for name in names)
            + "\n\nOptionale Werkzeuge werden nicht installiert. Fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.setEnabled(False)
        try:
            installed = self.tool_service.install_missing_required_plugin_tools()
            names = ", ".join(item["display_name"] for item in installed)
            QMessageBox.information(
                self,
                "Plugin-Werkzeuge",
                f"Erfolgreich installiert: {names}" if names else "Keine Installation erforderlich.",
            )
        except Exception as error:
            QMessageBox.critical(self, "Plugin-Werkzeuge", f"Installation fehlgeschlagen:\n\n{error}")
        finally:
            self.setEnabled(True)
            self.refresh()

    def redownload_tools(self) -> None:
        answer = QMessageBox.question(
            self,
            "MediaHub-Tools neu herunterladen",
            "yt-dlp, FFmpeg, FFprobe und Deno werden neu heruntergeladen.\n\n"
            "Plugin-Werkzeuge werden in diesem Schritt noch nicht verändert. Fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.setEnabled(False)
        try:
            self.tool_service.redownload_all_tools()
            QMessageBox.information(self, "Tool-Manager", "Die MediaHub-Tools wurden neu heruntergeladen.")
        except Exception as error:
            QMessageBox.critical(self, "Tool-Manager", f"Tool-Download fehlgeschlagen:\n\n{error}")
        finally:
            self.setEnabled(True)
            self.refresh()
