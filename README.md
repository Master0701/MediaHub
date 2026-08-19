# MediaHub v1.0.19

MediaHub ist ein lokales PySide6-Programm zum Verwalten von YouTube-Kanälen, Playlists, Video-Downloads, Plex-Importen und separat installierbaren Erweiterungen.

## Neu und verbessert in v1.0.19

# MediaHub v1.0.19

## Plugin-Store

- Download-Logik des MediaHub Plugin-Stores korrigiert.
- Plugin-Pakete werden jetzt aus dem gemeinsamen MediaHub_Plugins-Release geladen.
- Plugin-Version und gemeinsamer GitHub-Release-Tag werden nicht mehr fälschlich gleichgesetzt.
- Release-Assets werden über den jeweils neuesten gemeinsamen Plugin-Release aufgelöst.
- HTTP-404-Fehler beim automatischen Download aktueller MediaHub-Plugins behoben.
- Download des Metadata Editors v0.4.4 erfolgreich gegen das veröffentlichte GitHub-Asset getestet.
- AI-Node-Plugin-Assets ebenfalls gegen den gemeinsamen Release geprüft.

## Film- und Serienmetadaten

- Gemeinsame Metadaten-Unterstützung für Filme und Serien im MediaHub-Hauptprogramm erweitert.
- Datenbankschema um media_type, year, series, season, episode und episode_title erweitert.
- Repository-Unterstützung für die neuen Film- und Serienfelder ergänzt.
- Zentrale metadata.update-Schreibschnittstelle für Plugins erweitert.
- Bestätigte Metadata-Editor-Änderungen können zentral in MediaHub gespeichert werden.
- Regressionstests für das erweiterte Metadaten-Schema ergänzt.

## Plugin- und Tool-Infrastruktur

- Plugin-API um den Metadaten-Schreibzugriff erweitert.
- Tool-Pfad und Tool-Status können kontrolliert über die MediaHub-Plugin-API bereitgestellt werden.
- Lokale Plugin-Laufzeitdaten unter plugin_data/ werden vom Git-Repository ausgeschlossen.

## Datenbank

- SQLite-Verbindungen werden nach der Verwendung zuverlässig geschlossen.

## Qualitätssicherung

- MediaHub-Core-Tests erfolgreich.
- Metadaten-Schema-Regressionstests erfolgreich.
- Plugin-Downloader-Live-Test mit HTTP 200 erfolgreich.
- MediaHub-Arbeitsbaum vor der Release-Vorbereitung sauber.

Die vollständige Versionshistorie steht in [`CHANGELOG.md`](CHANGELOG.md).

## Start aus dem Quellcode

```powershell
python -m pip install -r requirements.txt
python main.py
```
