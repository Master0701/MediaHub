from __future__ import annotations

import json
import shutil
import threading
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QListWidgetItem, QWidget

from mediahub_web_core.server import acquire_shared_server, release_shared_server
from mediahub_web_core.settings import WebRuntimeSettingsStore, connection_info


class MediaHubMetadataEditorPlugin:
    """Lokaler, sicherer Metadaten- und NFO-Editor für MediaHub."""

    VERSION = "0.3.0"
    EDITABLE_FIELDS = (
        "title", "description", "year", "season", "episode",
        "series", "channel", "playlist", "published_at",
    )
    NFO_TAGS = {
        "title": "title", "description": "plot", "year": "year",
        "season": "season", "episode": "episode", "series": "showtitle",
        "channel": "studio", "playlist": "set", "published_at": "aired",
    }
    IMAGE_NAMES = {
        "poster": ("poster.jpg", "poster.png", "folder.jpg", "folder.png"),
        "fanart": ("fanart.jpg", "fanart.png", "background.jpg", "background.png"),
        "banner": ("banner.jpg", "banner.png"),
        "thumbnail": ("thumb.jpg", "thumb.png", "thumbnail.jpg", "thumbnail.png"),
    }
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, plugin_path: Path, mediahub_api=None):
        self.plugin_path = Path(plugin_path)
        self.mediahub_api = mediahub_api
        self.base_dir = Path(getattr(mediahub_api, "base_dir", self.plugin_path))
        self.settings_store = WebRuntimeSettingsStore(self.base_dir)
        self.settings = self.settings_store.load()
        self.server = acquire_shared_server(str(self.base_dir), self.settings.host, self.settings.port)
        self.data_dir = self.base_dir / "plugin_data" / "metadata_editor"
        self.drafts_file = self.data_dir / "drafts.json"
        self.backup_dir = self.data_dir / "backups"
        self._draft_lock = threading.Lock()
        self._register_routes()

    def start(self):
        self.server.start()

    def stop(self):
        release_shared_server(str(self.base_dir), owner=self)

    def get_plugin_settings(self):
        info = connection_info(self.settings)
        active_url = str(info.get("active_url") or "").rstrip("/")
        return {
            "version": self.VERSION,
            "url": f"{active_url}/metadata-editor" if active_url else "/metadata-editor",
            "drafts_file": str(self.drafts_file),
            "backup_dir": str(self.backup_dir),
            "write_api_available": self._write_api_available(),
            "direct_nfo_available": True,
        }

    def _register_routes(self):
        routes = {
            "/metadata-editor": self._index,
            "/metadata-editor/": self._index,
            "/metadata-editor/api/status": self._status,
            "/metadata-editor/api/library": self._library,
            "/metadata-editor/api/channels": self._channels,
            "/metadata-editor/api/playlists": self._playlists,
            "/metadata-editor/api/drafts": self._drafts,
            "/metadata-editor/assets/mediahub.css": self._stylesheet,
        }
        for path, handler in routes.items():
            self.server.add_route(path, handler, owner=self)
        for path, handler in {
            "/metadata-editor/api/preview": self._preview,
            "/metadata-editor/api/draft": self._save_draft,
            "/metadata-editor/api/commit": self._commit,
            "/metadata-editor/api/draft/delete": self._delete_draft,
            "/metadata-editor/api/inspect-files": self._inspect_files,
            "/metadata-editor/api/nfo/save": self._save_nfo,
            "/metadata-editor/api/image/replace": self._replace_image,
        }.items():
            self.server.add_post_route(path, handler, owner=self)

    def _index(self, request=None):
        return 200, "text/html; charset=utf-8", (self.plugin_path / "index.html").read_bytes()

    def _stylesheet(self, request=None):
        return 200, "text/css; charset=utf-8", (self.plugin_path / "assets" / "css" / "mediahub.css").read_bytes()

    @staticmethod
    def _json(data: Any, status: int = 200):
        return status, "application/json; charset=utf-8", json.dumps(data, ensure_ascii=False).encode("utf-8")

    def _api_call(self, method: str, default):
        if self.mediahub_api is None or not hasattr(self.mediahub_api, method):
            return default, False, f"{method} ist in dieser MediaHub-Version nicht verfügbar."
        try:
            return getattr(self.mediahub_api, method)(), True, ""
        except Exception as error:
            return default, False, str(error)

    def _status(self, request=None):
        return self._json({
            "available": True,
            "version": self.VERSION,
            "write_api_available": self._write_api_available(),
            "direct_nfo_available": True,
            "safe_mode": True,
            "message": "Medienbrowser, Metadaten-, NFO- und Bildverwaltung mit automatischer Sicherung sind verfügbar.",
        })

    def _library(self, request=None):
        data, available, message = self._api_call("get_library_videos", [])
        items = data.get("videos", data.get("items", [])) if isinstance(data, dict) else data
        return self._json({"available": available, "message": message, "items": self._normalize_items(items)}, 200 if available else 409)

    def _channels(self, request=None):
        data, available, message = self._api_call("get_channels", [])
        items = data.get("channels", data.get("items", [])) if isinstance(data, dict) else data
        return self._json({"available": available, "message": message, "items": items or []}, 200 if available else 409)

    def _playlists(self, request=None):
        data, available, message = self._api_call("get_playlists", [])
        items = data.get("playlists", data.get("items", [])) if isinstance(data, dict) else data
        return self._json({"available": available, "message": message, "items": items or []}, 200 if available else 409)

    def _normalize_items(self, items):
        result = []
        for position, raw in enumerate(items or []):
            item = dict(raw) if isinstance(raw, dict) else {"title": str(raw)}
            item_id = str(item.get("id") or item.get("video_id") or item.get("path") or position)
            normalized = {"id": item_id, **item}
            normalized.setdefault("title", item.get("name") or item.get("filename") or "Ohne Titel")
            normalized.setdefault("description", item.get("summary") or "")
            normalized.setdefault("year", item.get("release_year") or "")
            normalized.setdefault("season", item.get("season_number") or "")
            normalized.setdefault("episode", item.get("episode_number") or "")
            normalized.setdefault("series", item.get("series_name") or item.get("show") or "")
            normalized.setdefault("channel", item.get("channel_name") or "")
            normalized.setdefault("playlist", item.get("playlist_name") or "")
            normalized.setdefault("published_at", item.get("release_date") or item.get("published") or "")
            result.append(normalized)
        return result

    def _clean_changes(self, payload):
        source = dict(payload or {})
        original, edited = dict(source.get("original") or {}), dict(source.get("edited") or {})
        item_id = str(source.get("id") or edited.get("id") or original.get("id") or "").strip()
        changes = {}
        for field in self.EDITABLE_FIELDS:
            before, after = original.get(field, ""), edited.get(field, original.get(field, ""))
            if str(before).strip() != str(after).strip():
                changes[field] = {"before": before, "after": after}
        return item_id, original, edited, changes

    def _preview(self, payload, request=None):
        item_id, original, edited, changes = self._clean_changes(payload)
        if not item_id:
            return self._json({"ok": False, "message": "Der Medieneintrag besitzt keine ID."}, 400)
        return self._json({"ok": True, "id": item_id, "original": original, "edited": edited, "changes": changes, "change_count": len(changes)})

    def _drafts(self, request=None):
        drafts = self._read_drafts()
        return self._json({"ok": True, "items": list(drafts.values()), "count": len(drafts)})

    def _save_draft(self, payload, request=None):
        item_id, original, edited, changes = self._clean_changes(payload)
        if not item_id:
            return self._json({"ok": False, "message": "Der Medieneintrag besitzt keine ID."}, 400)
        draft = {"id": item_id, "title": str(edited.get("title") or original.get("title") or "Ohne Titel"), "original": original, "edited": edited, "changes": changes, "updated_at": datetime.now().isoformat(timespec="seconds")}
        with self._draft_lock:
            drafts = self._read_drafts_unlocked(); drafts[item_id] = draft; self._write_drafts_unlocked(drafts)
        return self._json({"ok": True, "message": "Metadaten-Entwurf gespeichert.", "draft": draft})

    def _delete_draft(self, payload, request=None):
        item_id = str((payload or {}).get("id") or "").strip()
        with self._draft_lock:
            drafts = self._read_drafts_unlocked(); removed = drafts.pop(item_id, None); self._write_drafts_unlocked(drafts)
        return self._json({"ok": bool(removed), "message": "Entwurf gelöscht." if removed else "Entwurf nicht gefunden."}, 200 if removed else 404)

    def _write_api_available(self):
        return self.mediahub_api is not None and hasattr(self.mediahub_api, "execute_action")

    def _commit(self, payload, request=None):
        item_id, original, edited, changes = self._clean_changes(payload)
        if not item_id or not changes:
            return self._json({"ok": False, "message": "Es sind keine speicherbaren Änderungen vorhanden."}, 400)
        if not self._write_api_available():
            return self._json({"ok": False, "draft_only": True, "message": "Die MediaHub-Datenbank kann noch nicht direkt aktualisiert werden. NFO-Dateien lassen sich bereits separat speichern."}, 409)
        args = {"id": item_id, "metadata": edited, "backup": deepcopy(original), "source": "mediahub.metadata_editor"}
        try:
            result = self.mediahub_api.execute_action("metadata.update", args)
        except Exception as error:
            return self._json({"ok": False, "message": str(error)}, 500)
        if not isinstance(result, dict):
            result = {"ok": bool(result), "message": "Metadaten-Aktion ausgeführt."}
        return self._json(result, 200 if result.get("ok") else 409)

    def _media_path(self, item: dict) -> Path | None:
        for key in ("path", "file_path", "filepath", "local_path", "filename"):
            value = str(item.get(key) or "").strip()
            if value:
                path = Path(value).expanduser()
                if path.exists():
                    return path.resolve()
        return None

    def _nfo_path(self, item: dict, media_path: Path | None) -> Path | None:
        explicit = str(item.get("nfo_path") or "").strip()
        if explicit:
            return Path(explicit).expanduser().resolve()
        if media_path is None:
            return None
        return (media_path / "tvshow.nfo") if media_path.is_dir() else media_path.with_suffix(".nfo")

    def _inspect_files(self, payload, request=None):
        item = dict((payload or {}).get("item") or {})
        media_path = self._media_path(item)
        nfo_path = self._nfo_path(item, media_path)
        nfo = {"path": str(nfo_path or ""), "exists": bool(nfo_path and nfo_path.exists()), "content": "", "error": ""}
        if nfo["exists"]:
            try:
                nfo["content"] = nfo_path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                nfo["error"] = "Die NFO-Datei ist nicht UTF-8-kodiert und wird aus Sicherheitsgründen nicht automatisch geändert."
            except Exception as error:
                nfo["error"] = str(error)
        folder = media_path if media_path and media_path.is_dir() else (media_path.parent if media_path else None)
        images = {}
        for kind, names in self.IMAGE_NAMES.items():
            found = next((folder / name for name in names if folder and (folder / name).exists()), None)
            images[kind] = {"exists": bool(found), "path": str(found or "")}
        return self._json({"ok": True, "media_path": str(media_path or ""), "folder": str(folder or ""), "nfo": nfo, "images": images})

    def _backup_file(self, source: Path, item_id: str, category: str) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in item_id)[:80] or "media"
        target_dir = self.backup_dir / safe_id / category
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{stamp}_{source.name}"
        shutil.copy2(source, target)
        return target

    @staticmethod
    def _set_xml_text(root: ET.Element, tag: str, value: Any):
        node = root.find(tag)
        if node is None:
            node = ET.SubElement(root, tag)
        node.text = str(value or "")

    def _save_nfo(self, payload, request=None):
        source = dict(payload or {})
        item = dict(source.get("item") or {})
        edited = dict(source.get("edited") or {})
        item_id = str(item.get("id") or edited.get("id") or "").strip()
        media_path = self._media_path(item)
        nfo_path = self._nfo_path(item, media_path)
        if not item_id or nfo_path is None:
            return self._json({"ok": False, "message": "Kein gültiger lokaler Medien- oder NFO-Pfad vorhanden."}, 400)
        if nfo_path.exists():
            try:
                raw = nfo_path.read_text(encoding="utf-8-sig")
                root = ET.fromstring(raw) if raw.strip() else ET.Element("episodedetails")
                backup = self._backup_file(nfo_path, item_id, "nfo")
            except UnicodeDecodeError:
                return self._json({"ok": False, "message": "NFO ist nicht UTF-8-kodiert. Keine Änderung durchgeführt."}, 409)
            except ET.ParseError as error:
                return self._json({"ok": False, "message": f"NFO enthält ungültiges XML: {error}"}, 409)
            except Exception as error:
                return self._json({"ok": False, "message": str(error)}, 500)
        else:
            root = ET.Element("episodedetails")
            backup = None
        for field, tag in self.NFO_TAGS.items():
            self._set_xml_text(root, tag, edited.get(field, item.get(field, "")))
        try:
            nfo_path.parent.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ")
            temporary = nfo_path.with_suffix(nfo_path.suffix + ".tmp")
            tree.write(temporary, encoding="utf-8", xml_declaration=True)
            temporary.replace(nfo_path)
        except Exception as error:
            return self._json({"ok": False, "message": f"NFO konnte nicht gespeichert werden: {error}"}, 500)
        return self._json({"ok": True, "message": "NFO UTF-8-sicher gespeichert.", "path": str(nfo_path), "backup": str(backup or "")})

    def _replace_image(self, payload, request=None):
        source = dict(payload or {})
        item = dict(source.get("item") or {})
        kind = str(source.get("kind") or "").strip().lower()
        source_path = Path(str(source.get("source_path") or "").strip()).expanduser()
        item_id = str(item.get("id") or "").strip()
        if kind not in self.IMAGE_NAMES:
            return self._json({"ok": False, "message": "Unbekannter Bildtyp."}, 400)
        if not source_path.is_file() or source_path.suffix.lower() not in self.IMAGE_EXTENSIONS:
            return self._json({"ok": False, "message": "Die ausgewählte Bilddatei wurde nicht gefunden oder besitzt kein unterstütztes Format."}, 400)
        media_path = self._media_path(item)
        folder = media_path if media_path and media_path.is_dir() else (media_path.parent if media_path else None)
        if folder is None or not folder.exists():
            return self._json({"ok": False, "message": "Der lokale Medienordner wurde nicht gefunden."}, 400)
        target = folder / f"{kind}{source_path.suffix.lower()}"
        existing = next((folder / name for name in self.IMAGE_NAMES[kind] if (folder / name).exists()), None)
        try:
            backup = self._backup_file(existing, item_id, f"images/{kind}") if existing else None
            shutil.copy2(source_path, target)
            if existing and existing != target and existing.exists():
                existing.unlink()
        except Exception as error:
            return self._json({"ok": False, "message": f"Bild konnte nicht ersetzt werden: {error}"}, 500)
        return self._json({"ok": True, "message": f"{kind.capitalize()} wurde ersetzt.", "path": str(target), "backup": str(backup or "")})

    def _read_drafts(self):
        with self._draft_lock:
            return self._read_drafts_unlocked()

    def _read_drafts_unlocked(self):
        if not self.drafts_file.exists():
            return {}
        try:
            data = json.loads(self.drafts_file.read_text(encoding="utf-8-sig"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_drafts_unlocked(self, drafts):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.drafts_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.drafts_file)

    def create_widget(self, parent=None):
        """Erzeugt die native Metadata-Editor-Oberfläche für MediaHub."""
        return NativeMetadataEditorWidget(self, parent=parent)


class NativeMetadataEditorWidget(QWidget):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QAbstractItemView, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
            QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
            QPushButton, QSpinBox, QSplitter, QTextEdit, QVBoxLayout, QWidget,
        )
        self.plugin = plugin
        self._items = []
        self._current = None
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Medien durchsuchen …")
        self.search.textChanged.connect(self._apply_filter)
        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(self.btn_refresh)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Kategorien"))
        self.categories = QListWidget()
        for text in ("Alle Medien", "Kanäle", "Serien", "Playlists", "Entwürfe"):
            self.categories.addItem(text)
        self.categories.setCurrentRow(0)
        self.categories.currentRowChanged.connect(self._apply_filter)
        left_layout.addWidget(self.categories, 1)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(QLabel("Medien"))
        self.media_list = QListWidget()
        self.media_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.media_list.currentRowChanged.connect(self._load_selected)
        center_layout.addWidget(self.media_list, 1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("Metadaten"))
        form = QFormLayout()
        self.title_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.description_edit.setMinimumHeight(100)
        self.year_edit = QSpinBox(); self.year_edit.setRange(0, 9999); self.year_edit.setSpecialValueText("")
        self.season_edit = QSpinBox(); self.season_edit.setRange(0, 9999)
        self.episode_edit = QSpinBox(); self.episode_edit.setRange(0, 99999)
        self.series_edit = QLineEdit()
        self.channel_edit = QLineEdit()
        self.playlist_edit = QLineEdit()
        self.date_edit = QLineEdit()
        self.path_label = QLabel("-")
        self.path_label.setWordWrap(True)
        form.addRow("Titel", self.title_edit)
        form.addRow("Beschreibung", self.description_edit)
        form.addRow("Jahr", self.year_edit)
        form.addRow("Staffel", self.season_edit)
        form.addRow("Episode", self.episode_edit)
        form.addRow("Serie", self.series_edit)
        form.addRow("Kanal", self.channel_edit)
        form.addRow("Playlist", self.playlist_edit)
        form.addRow("Veröffentlicht", self.date_edit)
        form.addRow("Pfad", self.path_label)
        right_layout.addLayout(form)

        self.diff_label = QLabel("Keine Änderungen")
        self.diff_label.setWordWrap(True)
        right_layout.addWidget(self.diff_label)

        buttons = QHBoxLayout()
        self.btn_draft = QPushButton("Entwurf speichern")
        self.btn_nfo = QPushButton("NFO speichern")
        self.btn_poster = QPushButton("Poster ersetzen")
        self.btn_reset = QPushButton("Zurücksetzen")
        self.btn_draft.clicked.connect(self._save_draft)
        self.btn_nfo.clicked.connect(self._save_nfo)
        self.btn_poster.clicked.connect(self._replace_poster)
        self.btn_reset.clicked.connect(self._reset_fields)
        for button in (self.btn_draft, self.btn_nfo, self.btn_poster, self.btn_reset):
            buttons.addWidget(button)
        right_layout.addLayout(buttons)
        right_layout.addStretch(1)

        for widget in (
            self.title_edit, self.description_edit, self.series_edit,
            self.channel_edit, self.playlist_edit, self.date_edit,
        ):
            widget.textChanged.connect(self._update_diff)
        for widget in (self.year_edit, self.season_edit, self.episode_edit):
            widget.valueChanged.connect(self._update_diff)

        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 4)
        splitter.setSizes([170, 320, 650])
        root.addWidget(splitter, 1)
        self.refresh()

    def refresh(self):
        try:
            raw = self.plugin.mediahub_api.get_library_videos() if self.plugin.mediahub_api else []
            self._items = self.plugin._normalize_items(raw)
            self._apply_filter()
        except Exception as error:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Metadata Editor", f"Bibliothek konnte nicht geladen werden:\n{error}")

    def _apply_filter(self, *args):
        query = self.search.text().strip().lower()
        category = self.categories.currentItem().text() if self.categories.currentItem() else "Alle Medien"
        drafts = self.plugin._read_drafts() if category == "Entwürfe" else {}
        self.media_list.blockSignals(True)
        self.media_list.clear()
        visible = []
        for item in self._items:
            if category == "Entwürfe" and str(item.get("id")) not in drafts:
                continue
            if category == "Kanäle" and not str(item.get("channel") or "").strip():
                continue
            if category == "Serien" and not str(item.get("series") or "").strip():
                continue
            if category == "Playlists" and not str(item.get("playlist") or "").strip():
                continue
            haystack = " ".join(str(item.get(key) or "") for key in ("title", "series", "channel", "playlist", "path")).lower()
            if query and query not in haystack:
                continue
            visible.append(item)
            text = str(item.get("title") or "Ohne Titel")
            context = str(item.get("series") or item.get("channel") or item.get("playlist") or "").strip()
            if context:
                text += f"\n{context}"
            row = QListWidgetItem(text)
            row.setData(256, item)
            self.media_list.addItem(row)
        self.media_list.blockSignals(False)
        if visible:
            self.media_list.setCurrentRow(0)
        else:
            self._current = None
            self._clear_fields()

    def _load_selected(self, row):
        item = self.media_list.item(row)
        self._current = dict(item.data(256) or {}) if item is not None else None
        if not self._current:
            self._clear_fields()
            return
        draft = self.plugin._read_drafts().get(str(self._current.get("id")))
        values = dict(draft.get("edited") or {}) if draft else self._current
        self._set_fields(values)

    def _set_fields(self, item):
        self._loading = True
        self.title_edit.setText(str(item.get("title") or ""))
        self.description_edit.setPlainText(str(item.get("description") or ""))
        self.year_edit.setValue(self._number(item.get("year")))
        self.season_edit.setValue(self._number(item.get("season")))
        self.episode_edit.setValue(self._number(item.get("episode")))
        self.series_edit.setText(str(item.get("series") or ""))
        self.channel_edit.setText(str(item.get("channel") or ""))
        self.playlist_edit.setText(str(item.get("playlist") or ""))
        self.date_edit.setText(str(item.get("published_at") or ""))
        path = item.get("path") or item.get("file_path") or item.get("filepath") or item.get("local_path") or item.get("filename") or "-"
        self.path_label.setText(str(path))
        self._loading = False
        self._update_diff()

    def _clear_fields(self):
        self._set_fields({})

    @staticmethod
    def _number(value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _edited(self):
        item = dict(self._current or {})
        item.update({
            "title": self.title_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "year": self.year_edit.value() or "",
            "season": self.season_edit.value(),
            "episode": self.episode_edit.value(),
            "series": self.series_edit.text().strip(),
            "channel": self.channel_edit.text().strip(),
            "playlist": self.playlist_edit.text().strip(),
            "published_at": self.date_edit.text().strip(),
        })
        return item

    def _update_diff(self, *args):
        if self._loading or not self._current:
            return
        _, _, _, changes = self.plugin._clean_changes({"id": self._current.get("id"), "original": self._current, "edited": self._edited()})
        if not changes:
            self.diff_label.setText("Keine Änderungen")
        else:
            self.diff_label.setText("Geändert: " + ", ".join(changes.keys()))

    def _save_draft(self):
        if not self._current:
            return
        status, _, body = self.plugin._save_draft({"id": self._current.get("id"), "original": self._current, "edited": self._edited()})
        self._show_result(status, body)

    def _save_nfo(self):
        if not self._current:
            return
        status, _, body = self.plugin._save_nfo({"item": self._current, "edited": self._edited()})
        self._show_result(status, body)

    def _replace_poster(self):
        from PySide6.QtWidgets import QFileDialog
        if not self._current:
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Poster auswählen", "", "Bilder (*.jpg *.jpeg *.png *.webp)")
        if not filename:
            return
        status, _, body = self.plugin._replace_image({"item": self._current, "kind": "poster", "source_path": filename})
        self._show_result(status, body)

    def _reset_fields(self):
        if self._current:
            self._set_fields(self._current)

    def _show_result(self, status, body):
        from PySide6.QtWidgets import QMessageBox
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            data = {"message": str(body)}
        message = str(data.get("message") or "Aktion abgeschlossen.")
        (QMessageBox.information if int(status) < 400 else QMessageBox.warning)(self, "Metadata Editor", message)
        self._update_diff()
