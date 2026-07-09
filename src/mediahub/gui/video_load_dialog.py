from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QRadioButton, QSpinBox
)


class VideoLoadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Videomenge auswählen")
        self.resize(360, 180)

        self.selected_limit = 20

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Wie viele Videos sollen ausgelesen werden?"))

        self.radio_count = QRadioButton("Eigene Anzahl")
        self.radio_all = QRadioButton("Alle Videos")
        self.radio_count.setChecked(True)

        self.count_box = QSpinBox()
        self.count_box.setMinimum(1)
        self.count_box.setMaximum(9999)
        self.count_box.setValue(20)

        layout.addWidget(self.radio_count)
        layout.addWidget(self.count_box)
        layout.addWidget(self.radio_all)

        buttons = QHBoxLayout()

        self.btn_ok = QPushButton("Weiter")
        self.btn_cancel = QPushButton("Abbrechen")

        self.btn_ok.clicked.connect(self.accept_selection)
        self.btn_cancel.clicked.connect(self.reject)

        buttons.addStretch()
        buttons.addWidget(self.btn_ok)
        buttons.addWidget(self.btn_cancel)

        layout.addLayout(buttons)

    def accept_selection(self):
        if self.radio_all.isChecked():
            self.selected_limit = None
        else:
            self.selected_limit = self.count_box.value()

        self.accept()