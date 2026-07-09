from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel
)
from PySide6.QtCore import Qt


class PlaylistSelectionDialog(QDialog):
    def __init__(self, playlists, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Playlists auswählen")
        self.resize(800, 500)

        self.playlists = playlists
        self.selected_playlists = []

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Wähle die Playlists aus:"))

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        for playlist in self.playlists:
            item = QListWidgetItem(playlist.get("title", "Ohne Titel"))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list_widget.addItem(item)

        button_row = QHBoxLayout()

        self.btn_all = QPushButton("Alle")
        self.btn_none = QPushButton("Keine")
        self.btn_ok = QPushButton("Weiter")
        self.btn_cancel = QPushButton("Abbrechen")

        self.btn_all.clicked.connect(self.select_all)
        self.btn_none.clicked.connect(self.select_none)
        self.btn_ok.clicked.connect(self.accept_selection)
        self.btn_cancel.clicked.connect(self.reject)

        button_row.addWidget(self.btn_all)
        button_row.addWidget(self.btn_none)
        button_row.addStretch()
        button_row.addWidget(self.btn_ok)
        button_row.addWidget(self.btn_cancel)

        layout.addLayout(button_row)

    def select_all(self):
        for index in range(self.list_widget.count()):
            self.list_widget.item(index).setCheckState(Qt.CheckState.Checked)

    def select_none(self):
        for index in range(self.list_widget.count()):
            self.list_widget.item(index).setCheckState(Qt.CheckState.Unchecked)

    def accept_selection(self):
        self.selected_playlists = []

        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)

            if item.checkState() == Qt.CheckState.Checked:
                self.selected_playlists.append(self.playlists[index])

        self.accept()