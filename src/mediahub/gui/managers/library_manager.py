class LibraryManager:
    """Kapselt Aktualisierungen der Bibliothek für spätere Erweiterungen."""

    def __init__(self, library_panel=None):
        self.library_panel = library_panel

    def refresh(self):
        if self.library_panel is not None:
            if hasattr(self.library_panel, "schedule_refresh"):
                self.library_panel.schedule_refresh()
            else:
                self.library_panel.refresh()
