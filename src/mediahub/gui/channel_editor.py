import re

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QComboBox, QCheckBox,
    QTabWidget, QWidget
)

from src.mediahub.services.profile_service import ProfileService


class ChannelEditor(QDialog):
    def __init__(self, channel=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Kanal bearbeiten")
        self.resize(760, 620)
        self.setMinimumSize(560, 420)

        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.tab_general = QWidget()
        self.tab_folders = QWidget()
        self.tab_download = QWidget()
        self.tab_metadata = QWidget()

        self.tabs.addTab(self.tab_general, "Allgemein")
        self.tabs.addTab(self.tab_folders, "Ordner")
        self.tabs.addTab(self.tab_download, "Download")
        self.tabs.addTab(self.tab_metadata, "Metadaten")

        self.build_general_tab()
        self.build_folders_tab()
        self.build_download_tab()
        self.build_metadata_tab()

        buttons = QHBoxLayout()
        self.btn_save = QPushButton("Speichern")
        self.btn_cancel = QPushButton("Abbrechen")

        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_cancel)
        main_layout.addLayout(buttons)

        if channel:
            self.load_channel(channel)

        self.url.textChanged.connect(self.auto_fill_name_from_url)

        self.update_preview()

    def build_general_tab(self):
        layout = QVBoxLayout(self.tab_general)

        self.name = QLineEdit()
        self.url = QLineEdit()

        self.profile = QComboBox()
        self.profile.addItems(ProfileService.names())

        self.add_row(layout, "Name", self.name)
        self.add_row(layout, "URL", self.url)
        self.add_row(layout, "Profil", self.profile)

        layout.addStretch()

    def build_folders_tab(self):
        layout = QVBoxLayout(self.tab_folders)

        self.work_folder = QLineEdit()
        self.target_folder = QLineEdit()
        self.poster = QLineEdit()
        self.fanart = QLineEdit()

        self.add_file_row(layout, "Arbeitsordner", self.work_folder, folder=True)
        self.add_file_row(layout, "Plex-Ziel", self.target_folder, folder=True)
        self.add_file_row(layout, "Poster", self.poster, folder=False)
        self.add_file_row(layout, "Fanart", self.fanart, folder=False)

        layout.addStretch()

    def build_download_tab(self):
        layout = QVBoxLayout(self.tab_download)

        self.audio_only = QCheckBox("Nur Audio herunterladen")

        self.container = QComboBox()
        self.container.addItems(["MKV", "MP4", "WebM"])

        self.resolution = QComboBox()
        self.resolution.addItems(["Beste", "4K", "1440p", "1080p", "720p", "480p"])

        self.audio_format = QComboBox()
        self.audio_format.addItems(["M4A", "MP3", "AAC", "FLAC", "OGG", "WAV"])

        layout.addWidget(self.audio_only)
        self.add_row(layout, "Container", self.container)
        self.add_row(layout, "Auflösung", self.resolution)
        self.add_row(layout, "Audioformat", self.audio_format)

        layout.addStretch()

    def build_metadata_tab(self):
        layout = QVBoxLayout(self.tab_metadata)

        self.filename_template = QComboBox()
        self.filename_template.setEditable(True)
        self.filename_template.addItems([
            "{title} S{season:02}E{episode:02}",
            "S{season:02}E{episode:02} {title}",
            "{title} (S{season:02}E{episode:02})",
            "{title} - S{season:02}E{episode:02}",
            "{series} - {title} S{season:02}E{episode:02}",
            "{series} - S{season:02}E{episode:02} - {title}",
        ])

        self.insert_dropdown = QComboBox()
        self.insert_dropdown.addItems([
            "Baustein einfügen...",
            "{title}",
            "{series}",
            "S{season:02}E{episode:02}",
            "{year}",
            "({year})",
            "-",
        ])
        self.insert_dropdown.currentIndexChanged.connect(self.insert_filename_part)

        self.preview_label = QLabel("Vorschau: -")
        self.preview_label.setStyleSheet(
            "background-color: #2B2B2B; border: 1px solid #555; padding: 8px; font-weight: bold;"
        )

        self.create_nfo = QCheckBox("NFO erzeugen")
        self.create_poster = QCheckBox("Poster erzeugen")
        self.create_fanart = QCheckBox("Fanart erzeugen")
        self.clean_work_folder = QCheckBox("Arbeitsordner nach Import leeren")

        self.add_row(layout, "Dateinamenschema", self.filename_template)
        self.add_row(layout, "Baustein", self.insert_dropdown)

        layout.addWidget(QLabel("Platzhalter: {title}, {series}, {year}, {season:02}, {episode:02}"))
        layout.addWidget(self.preview_label)

        self.filename_template.currentTextChanged.connect(self.update_preview)

        layout.addWidget(self.create_nfo)
        layout.addWidget(self.create_poster)
        layout.addWidget(self.create_fanart)
        layout.addWidget(self.clean_work_folder)

        layout.addStretch()

    def add_row(self, layout, label, widget):
        layout.addWidget(QLabel(label))
        layout.addWidget(widget)

    def add_file_row(self, layout, label, line_edit, folder=False):
        layout.addWidget(QLabel(label))

        row = QHBoxLayout()
        row.addWidget(line_edit)

        button = QPushButton("Durchsuchen")
        button.clicked.connect(lambda: self.browse(line_edit, folder))

        row.addWidget(button)
        layout.addLayout(row)

    def auto_fill_name_from_url(self):
        current_name = self.name.text().strip()

        if current_name and current_name != "Neuer Kanal":
            return

        name = self.extract_name_from_url(self.url.text())

        if name:
            self.name.setText(name)

    def extract_name_from_url(self, url: str) -> str:
        url = url.strip()

        if not url:
            return ""

        patterns = [
            r"youtube\.com/@([^/?#]+)",
            r"youtube\.com/c/([^/?#]+)",
            r"youtube\.com/user/([^/?#]+)",
            r"youtube\.com/channel/([^/?#]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return self.clean_channel_name(match.group(1))

        return ""

    def clean_channel_name(self, name: str) -> str:
        name = name.strip()
        name = name.replace("@", "")
        name = re.sub(r"[-_]+", " ", name)
        name = re.sub(r"\s+", " ", name)
        return name.strip() or "Neuer Kanal"

    def insert_filename_part(self, index):
        if index <= 0:
            return

        insert_text = self.insert_dropdown.currentText()
        line_edit = self.filename_template.lineEdit()

        cursor_position = line_edit.cursorPosition()
        current_text = line_edit.text()

        if insert_text == "-":
            insert_text = " - "

        new_text = (
            current_text[:cursor_position]
            + insert_text
            + current_text[cursor_position:]
        )

        line_edit.setText(new_text)
        line_edit.setCursorPosition(cursor_position + len(insert_text))

        self.insert_dropdown.setCurrentIndex(0)
        self.update_preview()

    def update_preview(self):
        template = self.filename_template.currentText().strip() or "{title} S{season:02}E{episode:02}"

        try:
            preview = template.format(
                title="HDMI Port Tauschen",
                series="Toms SMD Micro löten",
                year="2026",
                season=1,
                episode=1,
            )
        except Exception:
            preview = "Fehler im Schema"

        self.preview_label.setText(f"Vorschau: {preview}.mkv")

    def browse(self, line_edit, folder=False):
        if folder:
            path = QFileDialog.getExistingDirectory(self, "Ordner auswählen")
        else:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Bild auswählen",
                "",
                "Bilder (*.jpg *.jpeg *.png *.webp)"
            )

        if path:
            line_edit.setText(path)

    def load_channel(self, channel):
        self.name.setText(channel.name)
        self.url.setText(channel.url)

        self.work_folder.setText(channel.work_folder)
        self.target_folder.setText(channel.target_folder)
        self.poster.setText(channel.poster)
        self.fanart.setText(channel.fanart)

        self.profile.setCurrentText(channel.profile)
        self.audio_only.setChecked(channel.audio_only)

        self.filename_template.setCurrentText(channel.filename_template)

        self.container.setCurrentText(channel.container)
        self.resolution.setCurrentText(channel.resolution)
        self.audio_format.setCurrentText(channel.audio_format)

        self.create_nfo.setChecked(channel.create_nfo)
        self.create_poster.setChecked(channel.create_poster)
        self.create_fanart.setChecked(channel.create_fanart)
        self.clean_work_folder.setChecked(channel.clean_work_folder)

        self.update_preview()

    def apply_to_channel(self, channel):
        channel.name = self.name.text().strip() or "Neuer Kanal"
        channel.url = self.url.text().strip()

        channel.work_folder = self.work_folder.text().strip()
        channel.target_folder = self.target_folder.text().strip()

        channel.poster = self.poster.text().strip()
        channel.fanart = self.fanart.text().strip()

        channel.profile = self.profile.currentText()
        channel.audio_only = self.audio_only.isChecked()
        channel.filename_template = (
            self.filename_template.currentText().strip()
            or "{title} S{season:02}E{episode:02}"
        )

        channel.container = self.container.currentText()
        channel.resolution = self.resolution.currentText()
        channel.audio_format = self.audio_format.currentText()

        channel.create_nfo = self.create_nfo.isChecked()
        channel.create_poster = self.create_poster.isChecked()
        channel.create_fanart = self.create_fanart.isChecked()
        channel.clean_work_folder = self.clean_work_folder.isChecked()

        return channel