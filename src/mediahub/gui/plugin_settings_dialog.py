from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
)


class WebPluginSettingsDialog(QDialog):
    def __init__(self, plugin_instance, parent=None):
        super().__init__(parent)
        self.plugin = plugin_instance
        self.setWindowTitle("WebRemote-Einstellungen")
        self.setMinimumWidth(620)
        self.data = dict(self.plugin.get_plugin_settings() or {})

        layout = QVBoxLayout(self)
        intro = QLabel("Diese Einstellungen gelten für die gemeinsame Web-Runtime und später auch für das Mobile Dashboard.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItem("Nur dieser Computer", "computer_only")
        self.mode.addItem("Im Heimnetz erreichbar", "home_network")
        index = self.mode.findData(self.data.get("network_mode", "computer_only"))
        self.mode.setCurrentIndex(max(index, 0))
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        self.port.setValue(int(self.data.get("port", 8765)))
        self.device_name = QLineEdit(str(self.data.get("device_name") or "MediaHub-PC"))
        self.pairing_required = QCheckBox("Nur gekoppelte Geräte zulassen")
        self.pairing_required.setChecked(bool(self.data.get("pairing_required", True)))
        form.addRow("Zugriff:", self.mode)
        form.addRow("Port:", self.port)
        form.addRow("Gerätename:", self.device_name)
        form.addRow("Sicherheit:", self.pairing_required)
        layout.addLayout(form)

        self.address = QLabel()
        self.address.setWordWrap(True)
        self.address.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.address)

        pairing_row = QHBoxLayout()
        qr_box = QVBoxLayout()
        qr_title = QLabel("QR-Code zur Kopplung")
        qr_title.setStyleSheet("font-weight: 700;")
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setMinimumSize(230, 230)
        self.qr_label.setStyleSheet("background: white; border: 1px solid #555; border-radius: 8px;")
        self.code_label = QLabel()
        self.code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        qr_box.addWidget(qr_title)
        qr_box.addWidget(self.qr_label)
        qr_box.addWidget(self.code_label)
        pairing_row.addLayout(qr_box)

        devices_box = QVBoxLayout()
        devices_title = QLabel("Gekoppelte Geräte")
        devices_title.setStyleSheet("font-weight: 700;")
        self.devices = QListWidget()
        self.devices.setMinimumHeight(180)
        device_buttons = QHBoxLayout()
        revoke = QPushButton("Ausgewähltes Gerät entfernen")
        revoke_all = QPushButton("Alle entfernen")
        rotate = QPushButton("Neuen Einmalcode erzeugen")
        revoke.clicked.connect(self._revoke_selected)
        revoke_all.clicked.connect(self._revoke_all)
        rotate.clicked.connect(self._rotate_code)
        device_buttons.addWidget(revoke)
        device_buttons.addWidget(revoke_all)
        devices_box.addWidget(devices_title)
        devices_box.addWidget(self.devices)
        devices_box.addLayout(device_buttons)
        devices_box.addWidget(rotate)
        pairing_row.addLayout(devices_box, 1)
        layout.addLayout(pairing_row)

        note = QLabel("Die Freigabe gilt nur im lokalen Netzwerk. MediaHub richtet keine Internetfreigabe und keine Router-Portfreigabe ein.")
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QHBoxLayout()
        save = QPushButton("Speichern")
        cancel = QPushButton("Abbrechen")
        save.clicked.connect(self._save)
        cancel.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

        self._refresh(self.data)

    def _refresh(self, data):
        self.data = dict(data or {})
        self.address.setText(
            f"Lokale Adresse: {self.data.get('local_url') or '-'}\n"
            f"Heimnetz-Adresse: {self.data.get('network_url') or 'Keine private IPv4-Adresse erkannt'}"
        )
        self.code_label.setText(f"Einmalcode: {self.data.get('pairing_code') or '-'}")
        self._draw_qr(self.data.get("pairing_qr_matrix") or [])
        self.devices.clear()
        for device in list(self.data.get("paired_devices") or []):
            text = f"{device.get('name') or 'Unbekanntes Gerät'}\nZuletzt: {device.get('last_seen') or '-'}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, str(device.get("id") or ""))
            self.devices.addItem(item)
        if self.devices.count() == 0:
            item = QListWidgetItem("Noch kein Gerät gekoppelt")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.devices.addItem(item)

    def _draw_qr(self, matrix):
        if not matrix:
            self.qr_label.setText("QR-Code nicht verfügbar")
            self.qr_label.setPixmap(QPixmap())
            return
        size = len(matrix)
        scale = max(4, 220 // max(size, 1))
        image = QImage(size * scale, size * scale, QImage.Format.Format_RGB32)
        image.fill(QColor("white"))
        for y, row in enumerate(matrix):
            for x, dark in enumerate(row):
                if dark:
                    for py in range(y * scale, (y + 1) * scale):
                        for px in range(x * scale, (x + 1) * scale):
                            image.setPixelColor(px, py, QColor("black"))
        self.qr_label.setText("")
        self.qr_label.setPixmap(QPixmap.fromImage(image).scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation))

    def _current_payload(self):
        return {
            "network_mode": self.mode.currentData(),
            "port": self.port.value(),
            "device_name": self.device_name.text().strip(),
            "pairing_required": self.pairing_required.isChecked(),
        }

    def _apply(self, extra=None, show_message=False):
        payload = self._current_payload()
        payload.update(dict(extra or {}))
        result = self.plugin.update_plugin_settings(payload)
        if not result.get("ok"):
            raise RuntimeError(str(result.get("message") or "Einstellungen konnten nicht gespeichert werden."))
        self._refresh(result)
        if show_message:
            QMessageBox.information(self, "WebRemote", str(result.get("message") or "Einstellungen gespeichert."))
        return result

    def _save(self):
        try:
            self._apply(show_message=True)
        except Exception as error:
            QMessageBox.warning(self, "WebRemote", str(error))
            return
        self.accept()

    def _rotate_code(self):
        try:
            self._apply({"rotate_pairing_code": True})
        except Exception as error:
            QMessageBox.warning(self, "WebRemote", str(error))

    def _revoke_selected(self):
        item = self.devices.currentItem()
        device_id = str(item.data(Qt.ItemDataRole.UserRole) or "") if item else ""
        if not device_id:
            return
        if QMessageBox.question(self, "WebRemote", "Dieses Gerät wirklich entfernen?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._apply({"revoke_device_id": device_id})
        except Exception as error:
            QMessageBox.warning(self, "WebRemote", str(error))

    def _revoke_all(self):
        if QMessageBox.question(self, "WebRemote", "Alle gekoppelten Geräte entfernen?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._apply({"revoke_all_devices": True})
        except Exception as error:
            QMessageBox.warning(self, "WebRemote", str(error))
