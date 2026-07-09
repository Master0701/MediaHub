class StatisticsManager:
    """Brücke zwischen Repository, Dashboard und Statistik-Center."""

    def __init__(self, repository=None, dashboard_panel=None, statistics_panel=None):
        self.repository = repository
        self.dashboard_panel = dashboard_panel
        self.statistics_panel = statistics_panel

    def refresh_dashboard(self):
        if self.dashboard_panel is not None:
            self.dashboard_panel.refresh()

    def refresh_statistics(self):
        if self.statistics_panel is not None:
            self.statistics_panel.refresh()

    def refresh_all(self):
        self.refresh_dashboard()
        self.refresh_statistics()
