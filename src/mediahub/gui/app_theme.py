def dark_theme():
    return """
        QMainWindow, QWidget {
            background-color: #202124;
            color: white;
        }

        QMenuBar {
            background-color: #2B2B2B;
            color: white;
        }

        QMenuBar::item:selected {
            background-color: #3A3A3A;
        }

        QMenu {
            background-color: #2B2B2B;
            color: white;
            border: 1px solid #444;
        }

        QMenu::item:selected {
            background-color: #F9A825;
            color: black;
        }

        QToolBar {
            background-color: #2B2B2B;
            border-bottom: 1px solid #444;
            spacing: 8px;
        }

        QToolButton {
            background-color: #F9A825;
            color: black;
            padding: 6px;
            font-weight: bold;
        }

        QLabel, QCheckBox, QGroupBox {
            color: white;
        }

        QListWidget, QTextEdit, QComboBox, QLineEdit, QSpinBox, QTableWidget {
            background-color: #2B2B2B;
            color: white;
            border: 1px solid #444;
            padding: 6px;
        }

        QPushButton {
            background-color: #F9A825;
            color: black;
            border: none;
            padding: 8px;
            font-weight: bold;
        }

        QPushButton:hover, QToolButton:hover {
            background-color: #FFC107;
        }

        QProgressBar {
            background-color: #2B2B2B;
            color: white;
            border: 1px solid #444;
            text-align: center;
        }

        QProgressBar::chunk {
            background-color: #F9A825;
        }

        QGroupBox {
            border: 1px solid #444;
            margin-top: 10px;
            padding: 10px;
            font-weight: bold;
        }

        QStatusBar {
            background-color: #2B2B2B;
            color: white;
            border-top: 1px solid #444;
        }

        QSplitter::handle {
            background-color: #444;
        }
    """