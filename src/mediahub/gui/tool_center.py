from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
)


class ToolCenter(QDialog):
    def __init__(self, tool_service, parent=None):
        super().__init__(parent)

        self.tool_service = tool_service

        self.setWindowTitle("Tool-Center")
        self.resize(700, 450)

        layout = QVBoxLayout(self)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        buttons = QHBoxLayout()

        self.btn_check = QPushButton("Tools prüfen")
        self.btn_open = QPushButton("Tools-Ordner öffnen")
        self.btn_redownload = QPushButton("Tools neu herunterladen")
        self.btn_close = QPushButton("Schließen")

        self.btn_check.clicked.connect(self.check_tools)
        self.btn_open.clicked.connect(self.tool_service.open_tools_folder)
        self.btn_redownload.clicked.connect(self.redownload_tools)
        self.btn_close.clicked.connect(self.close)

        buttons.addWidget(self.btn_check)
        buttons.addWidget(self.btn_open)
        buttons.addWidget(self.btn_redownload)
        buttons.addWidget(self.btn_close)

        layout.addLayout(buttons)

        self.check_tools()

    def log(self, message):
        self.output.append(message)

    def check_tools(self):
        self.output.clear()

        self.log("Tool-Status:")
        tools = self.tool_service.check_tools()

        for name, exists in tools.items():
            self.log(f"{'✓' if exists else '✗'} {name}")

        self.log("")
        self.log("Versionen:")

        versions = self.tool_service.get_tool_versions()
        for name, version in versions.items():
            self.log(f"{name}: {version}")

    def redownload_tools(self):
        self.output.clear()
        self.log("Tools werden neu heruntergeladen...")
        self.tool_service.redownload_all_tools(self.log)
        self.log("")
        self.check_tools()