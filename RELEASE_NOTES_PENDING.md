# MediaHub v1.0.19

## Plugin-Store

- Download-Logik des MediaHub Plugin-Stores korrigiert.
- Plugin-Pakete werden jetzt aus dem gemeinsamen MediaHub_Plugins-Release geladen.
- Plugin-Version und gemeinsamer GitHub-Release-Tag werden nicht mehr f?lschlich gleichgesetzt.
- Release-Assets werden ?ber den jeweils neuesten gemeinsamen Plugin-Release aufgel?st.
- HTTP-404-Fehler beim automatischen Download aktueller MediaHub-Plugins behoben.
- Download des Metadata Editors v0.4.4 erfolgreich gegen das ver?ffentlichte GitHub-Asset getestet.
- AI-Node-Plugin-Assets ebenfalls gegen den gemeinsamen Release gepr?ft.

## Film- und Serienmetadaten

- Gemeinsame Metadaten-Unterst?tzung f?r Filme und Serien im MediaHub-Hauptprogramm erweitert.
- Datenbankschema um media_type, year, series, season, episode und episode_title erweitert.
- Repository-Unterst?tzung f?r die neuen Film- und Serienfelder erg?nzt.
- Zentrale metadata.update-Schreibschnittstelle f?r Plugins erweitert.
- Best?tigte Metadata-Editor-?nderungen k?nnen zentral in MediaHub gespeichert werden.
- Regressionstests f?r das erweiterte Metadaten-Schema erg?nzt.

## Plugin- und Tool-Infrastruktur

- Plugin-API um den Metadaten-Schreibzugriff erweitert.
- Tool-Pfad und Tool-Status k?nnen kontrolliert ?ber die MediaHub-Plugin-API bereitgestellt werden.
- Lokale Plugin-Laufzeitdaten unter plugin_data/ werden vom Git-Repository ausgeschlossen.

## Datenbank

- SQLite-Verbindungen werden nach der Verwendung zuverl?ssig geschlossen.

## Qualit?tssicherung

- MediaHub-Core-Tests erfolgreich.
- Metadaten-Schema-Regressionstests erfolgreich.
- Plugin-Downloader-Live-Test mit HTTP 200 erfolgreich.
- MediaHub-Arbeitsbaum vor der Release-Vorbereitung sauber.
