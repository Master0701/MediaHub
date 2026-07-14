# Metadata Editor v0.3.0

Öffne den Metadata Editor über die Plugin-Verwaltung oder direkt unter `/metadata-editor`.

## Oberfläche

1. Links wählst du zwischen allen Medien, Kanälen, Serien, Playlists und Entwürfen.
2. In der mittleren Spalte suchst und filterst du die Bibliothek.
3. Rechts bearbeitest du Metadaten, NFO-Dateien und Bilder.

Der Live-Vergleich zeigt jede Änderung sofort an. Entwürfe verändern die MediaHub-Datenbank nicht. Vor Änderungen an NFO-Dateien oder Bildern wird automatisch eine Sicherung unter `plugin_data/metadata_editor/backups` erstellt.

Die Schaltfläche „MediaHub-Datenbank speichern“ ist nur aktiv, wenn das Hauptprogramm die kontrollierte Aktion `metadata.update` bereitstellt.
