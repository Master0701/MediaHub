from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QProgressBar, QListWidget, QListWidgetItem


class ChannelWizardProgressPanel(QGroupBox):
    def __init__(self, steps):
        super().__init__("Fortschritt")

        self.steps = steps

        layout = QVBoxLayout(self)

        self.progress = QProgressBar()
        self.progress.setRange(0, len(self.steps))
        self.progress.setValue(0)

        self.step_list = QListWidget()

        for step in self.steps:
            item = QListWidgetItem(f"☐ {step}")
            self.step_list.addItem(item)

        layout.addWidget(self.progress)
        layout.addWidget(self.step_list)

    def reset(self):
        self.progress.setValue(0)

        for index, step in enumerate(self.steps):
            self.step_list.item(index).setText(f"☐ {step}")

    def set_running(self, index):
        self.step_list.item(index).setText(f"⟳ {self.steps[index]}")

    def set_done(self, index):
        self.step_list.item(index).setText(f"✓ {self.steps[index]}")

    def set_warning(self, index):
        self.step_list.item(index).setText(f"! {self.steps[index]}")

    def set_progress(self, value):
        self.progress.setValue(value)