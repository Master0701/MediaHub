from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from src.mediahub.plugins.plugin_api import PluginInfo


class PluginLoader:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.plugins_dir = self.base_dir / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def discover(self) -> list[PluginInfo]:
        plugins: list[PluginInfo] = []
        for manifest in sorted(self.plugins_dir.glob("*/plugin.json")):
            plugin = self.load_manifest(manifest)
            if plugin is not None:
                plugins.append(plugin)
        return plugins


    @staticmethod
    def _parse_tool_declarations(required_values, optional_values) -> tuple[list[str], list[str]]:
        """Normalisiert alte Stringlisten und neue Tool-Objekte.

        Unterstützte Beispiele::

            "required_tools": ["mediainfo"]

            "required_tools": [
                {"id": "mediainfo", "required": False}
            ]

        Ein Objekt mit ``required: false`` wird als optional verwendet
        eingeordnet. Doppelte Einträge werden entfernt; Pflicht hat Vorrang.
        Zusätzliche Objektfelder bleiben für zukünftige Manifest-Erweiterungen
        erlaubt und werden vom aktuellen Loader bewusst ignoriert.
        """

        required: list[str] = []
        optional: list[str] = []

        def add_unique(target: list[str], tool_id: str) -> None:
            normalized = str(tool_id or "").strip().lower()
            if normalized and normalized not in target:
                target.append(normalized)

        def consume(values, default_required: bool) -> None:
            if not isinstance(values, list):
                return

            for value in values:
                is_required = default_required
                if isinstance(value, dict):
                    raw_id = value.get("id") or value.get("tool_id") or value.get("name")
                    if "required" in value:
                        is_required = bool(value.get("required"))
                else:
                    raw_id = value

                tool_id = str(raw_id or "").strip().lower()
                if not tool_id:
                    continue

                add_unique(required if is_required else optional, tool_id)

        consume(required_values, True)
        consume(optional_values, False)

        # Ein Pflichttool darf nicht zusätzlich als optional erscheinen.
        optional = [tool_id for tool_id in optional if tool_id not in required]
        return required, optional

    def load_manifest(self, manifest: Path) -> PluginInfo | None:
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            return None

        plugin_id = str(data.get("id") or manifest.parent.name).strip()
        if not plugin_id:
            return None

        permissions = data.get("permissions") or []
        if not isinstance(permissions, list):
            permissions = []

        required_tools, optional_tools = self._parse_tool_declarations(
            data.get("required_tools") or [],
            data.get("optional_tools") or [],
        )

        ui = data.get("ui") or {}
        if not isinstance(ui, dict):
            ui = {}
        has_gui = bool(ui.get("enabled", data.get("has_gui", data.get("type") == "web")))
        ui_type = str(ui.get("type") or ("web" if data.get("type") == "web" else "native"))
        try:
            ui_order = int(ui.get("order", 100))
        except (TypeError, ValueError):
            ui_order = 100
        web_ui = ui.get("web") or {}
        if not isinstance(web_ui, dict):
            web_ui = {}
        try:
            web_ui_order = int(web_ui.get("order", ui_order))
        except (TypeError, ValueError):
            web_ui_order = ui_order

        return PluginInfo(
            plugin_id=plugin_id,
            name=str(data.get("name") or plugin_id),
            version=str(data.get("version") or "0.1.0"),
            author=str(data.get("author") or "Unbekannt"),
            description=str(data.get("description") or ""),
            plugin_type=str(data.get("type") or "tool"),
            enabled=bool(data.get("enabled", True)),
            path=manifest.parent,
            entry=str(data.get("entry") or ""),
            icon=str(data.get("icon") or ""),
            safe_mode=bool(data.get("safe_mode", True)),
            class_name=str(data.get("class_name") or ""),
            minimum_mediahub_version=str(data.get("minimum_mediahub_version") or ""),
            permissions=[str(item) for item in permissions],
            required_tools=required_tools,
            optional_tools=optional_tools,
            has_gui=has_gui,
            ui_type=ui_type,
            ui_title=str(ui.get("title") or data.get("gui_name") or data.get("name") or plugin_id),
            ui_route=str(ui.get("route") or data.get("gui_route") or ""),
            ui_icon=str(ui.get("icon") or data.get("gui_icon") or "🧩"),
            ui_order=ui_order,
            has_settings=bool(data.get("has_settings", False)),
            web_ui_enabled=bool(web_ui.get("enabled", False)),
            web_ui_title=str(web_ui.get("title") or ui.get("title") or data.get("name") or plugin_id),
            web_ui_route=str(web_ui.get("route") or ui.get("route") or ""),
            web_ui_icon=str(web_ui.get("icon") or ui.get("icon") or "🧩"),
            web_ui_order=web_ui_order,
            web_ui_shell=bool(web_ui.get("shell", False)),
        )


    def _tool_license_acceptance_path(self) -> Path:
        return self.base_dir / "config" / "tool_license_acceptances.json"

    def _load_tool_license_acceptances(self) -> dict:
        path = self._tool_license_acceptance_path()
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _has_tool_license_acceptance(self, key: str) -> bool:
        normalized = str(key or "").strip()
        if not normalized:
            return True
        return normalized in self._load_tool_license_acceptances()

    def _record_tool_license_acceptance(
        self,
        key: str,
        *,
        tool_id: str,
        plugin_id: str,
    ) -> None:
        normalized = str(key or "").strip()
        if not normalized:
            return
        path = self._tool_license_acceptance_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._load_tool_license_acceptances()
        data[normalized] = {
            "tool_id": str(tool_id),
            "plugin_id": str(plugin_id),
            "accepted_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _confirm_tool_license(
        self,
        *,
        tool_id: str,
        plugin: PluginInfo,
        config: dict,
    ) -> bool:
        acceptance = config.get("license_acceptance") or {}
        if not isinstance(acceptance, dict):
            return True

        key = str(acceptance.get("key") or "").strip()
        if self._has_tool_license_acceptance(key):
            return True

        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
        except Exception:
            return False

        if QApplication.instance() is None:
            return False

        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle(
            str(acceptance.get("title") or "Lizenzhinweis")
        )
        box.setText(
            str(
                acceptance.get("text")
                or f"{tool_id} benötigt eine Lizenzbestätigung."
            )
        )
        box.setInformativeText(
            str(acceptance.get("details") or "")
        )
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.Cancel
        )
        yes_button = box.button(QMessageBox.StandardButton.Yes)
        cancel_button = box.button(QMessageBox.StandardButton.Cancel)
        if yes_button is not None:
            yes_button.setText(
                str(
                    acceptance.get("accept_button")
                    or "Ja, installieren"
                )
            )
        if cancel_button is not None:
            cancel_button.setText(
                str(acceptance.get("cancel_button") or "Abbrechen")
            )
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)

        accepted = (
            box.exec() == QMessageBox.StandardButton.Yes
        )
        if accepted:
            self._record_tool_license_acceptance(
                key,
                tool_id=tool_id,
                plugin_id=plugin.plugin_id,
            )
        return accepted

    def _install_declared_tools_after_plugin_install(
        self,
        plugin: PluginInfo,
        manifest_data: dict,
        installed_plugin_dir: Path,
    ) -> list[str]:
        """Installiert ausdrücklich freigegebene Plugin-Tools sichtbar mit.

        Die Plugin-Installation selbst ist die Benutzerbestätigung. Der
        automatische Tool-Schritt wird nur ausgeführt, wenn das Manifest
        ``install_declared_tools_on_plugin_install`` aktiviert.

        Pflichttool-Fehler brechen die Plugin-Installation ab. Optionale
        Tool-Fehler werden als Warnung zurückgegeben; das Plugin bleibt mit
        seinen eigenen Fallbacks nutzbar.
        """

        if not bool(
            manifest_data.get(
                "install_declared_tools_on_plugin_install",
                False,
            )
        ):
            return []

        from src.mediahub.services.tool_service import ToolService

        tool_service = ToolService(self.base_dir)
        required_tools = list(plugin.required_tools or [])
        optional_tools = [
            tool_id
            for tool_id in list(plugin.optional_tools or [])
            if tool_id not in required_tools
        ]

        messages: list[str] = []
        declared = [
            *(("required", tool_id) for tool_id in required_tools),
            *(("optional", tool_id) for tool_id in optional_tools),
        ]

        tool_setup = manifest_data.get("tool_setup") or {}
        if not isinstance(tool_setup, dict):
            tool_setup = {}

        for importance, tool_id in declared:
            setup_config = tool_setup.get(tool_id) or {}
            if not isinstance(setup_config, dict):
                setup_config = {}

            status = tool_service.find_tool_status(
                tool_id,
                include_version=False,
            )
            if status is None:
                message = f"Unbekanntes Plugin-Tool: {tool_id}"
                if importance == "required":
                    raise RuntimeError(message)
                messages.append(f"WARNUNG: {message}")
                continue

            display_name = str(
                status.get("display_name") or tool_id
            )
            already_installed = bool(status.get("installed"))

            if not self._confirm_tool_license(
                tool_id=tool_id,
                plugin=plugin,
                config=setup_config,
            ):
                message = (
                    f"{display_name} wurde nicht installiert, weil der "
                    "Lizenzhinweis nicht bestätigt wurde."
                )
                if importance == "required":
                    raise RuntimeError(message)
                messages.append(f"WARNUNG: {message}")
                continue

            if already_installed:
                messages.append(
                    f"Tool bereits vorhanden: {display_name}"
                )

            if already_installed:
                installed = status
            elif not bool(status.get("can_install")):
                message = (
                    f"Für {display_name} ist keine automatische "
                    "portable Installation verfügbar."
                )
                if importance == "required":
                    raise RuntimeError(message)
                messages.append(f"WARNUNG: {message}")
                continue

            if not already_installed:
                messages.append(
                    f"Tool wird portabel eingerichtet: {display_name}"
                )
            try:
                if not already_installed:
                    installed = tool_service.install_plugin_tool(tool_id)

                defaults_dir = str(
                    setup_config.get("defaults_dir") or ""
                ).strip()
                if defaults_dir:
                    copied = tool_service.apply_plugin_tool_defaults(
                        tool_id,
                        installed_plugin_dir / defaults_dir,
                        overwrite=bool(
                            setup_config.get(
                                "overwrite_defaults_on_fresh_install",
                                True,
                            )
                            and not already_installed
                        ),
                    )
                    if copied:
                        messages.append(
                            f"MediaHub-Konfiguration übernommen: "
                            f"{len(copied)} Datei(en)"
                        )
            except Exception as error:
                message = (
                    f"{display_name} konnte nicht eingerichtet werden: "
                    f"{error}"
                )
                if importance == "required":
                    raise RuntimeError(message) from error
                messages.append(f"WARNUNG: {message}")
                continue

            path = installed.get("path")
            messages.append(
                (
                    f"Tool einsatzbereit: {display_name}"
                    if already_installed
                    else f"Tool eingerichtet: {display_name}"
                )
                + (f" ({path})" if path else "")
            )

        return messages

    def _safe_extract(self, archive: zipfile.ZipFile, target: Path) -> None:
        target_resolved = target.resolve()
        for member in archive.infolist():
            destination = (target / member.filename).resolve()
            if destination != target_resolved and target_resolved not in destination.parents:
                raise ValueError(f"Unsicherer Pfad im Plugin-Paket: {member.filename}")
        archive.extractall(target)

    def install_mhplugin(self, file_path: Path) -> tuple[bool, str]:
        file_path = Path(file_path)
        if not file_path.exists():
            return False, "Plugin-Datei wurde nicht gefunden."
        if file_path.suffix.lower() != ".mhplugin":
            return False, "Nur .mhplugin-Dateien werden unterstützt."

        temp_dir = self.plugins_dir / "_install_temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(file_path, "r") as zip_file:
                self._safe_extract(zip_file, temp_dir)

            manifest_files = list(temp_dir.glob("*/plugin.json")) or list(temp_dir.glob("plugin.json"))
            if not manifest_files:
                return False, "Keine plugin.json im Plugin gefunden."

            manifest = manifest_files[0]
            manifest_data = json.loads(
                manifest.read_text(encoding="utf-8")
            )
            plugin = self.load_manifest(manifest)
            if plugin is None:
                return False, "plugin.json ist ungültig."
            if not plugin.entry:
                return False, "Das Plugin enthält keinen Entry-Point."

            entry_file = manifest.parent / plugin.entry
            if not entry_file.is_file():
                return False, f"Entry-Datei fehlt: {plugin.entry}"

            target_dir = self.plugins_dir / plugin.plugin_id
            if target_dir.exists():
                shutil.rmtree(target_dir)

            source_dir = temp_dir if manifest.parent == temp_dir else manifest.parent
            shutil.copytree(source_dir, target_dir)

            try:
                tool_messages = (
                    self._install_declared_tools_after_plugin_install(
                        plugin,
                        manifest_data,
                        target_dir,
                    )
                )
            except Exception:
                shutil.rmtree(target_dir, ignore_errors=True)
                raise

            message_lines = [
                f"Plugin installiert: {plugin.name} v{plugin.version}"
            ]
            message_lines.extend(tool_messages)
            return True, "\n".join(message_lines)
        except Exception as error:
            return False, f"Plugin konnte nicht installiert werden:\n{error}"
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def uninstall(self, plugin: PluginInfo) -> tuple[bool, str]:
        try:
            if plugin.path.exists():
                shutil.rmtree(plugin.path)
            return True, f"Plugin entfernt: {plugin.name}"
        except Exception as error:
            return False, f"Plugin konnte nicht entfernt werden:\n{error}"
