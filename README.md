# MediaHub v1.0.16

MediaHub ist ein lokales PySide6-Programm zum Verwalten von YouTube-Kanälen, Playlists, Video-Downloads, Plex-Importen und separat installierbaren Erweiterungen.

## Neu und verbessert in v1.0.16

## Zentrale Plugin-Werkzeugverwaltung

- Plugin-Werkzeuge werden aus einfachen IDs und strukturierten Objekten in `plugin.json` erkannt.
- Pflicht- und optionale Werkzeuge werden bei der Plugin-Installation berücksichtigt.
- Bereits vorhandene Werkzeuge werden erkannt und übersprungen.
- Fehlende Werkzeuge werden automatisch eingerichtet.

## Portable Werkzeuge ohne Administratorrechte

- MediaInfo wird portabel unter `MediaHub\tools` eingerichtet.
- MKVToolNix wird als offizielles `.7z`-Archiv geladen und portabel entpackt.
- Tesseract OCR wird als portables Paket aus dem Repository `MediaHub_Tools` installiert.
- FFprobe wird korrekt als von Plugins verwendetes Werkzeug registriert.

## Tool-Assistent und globale Einstellungen

- Der Tool-Assistent öffnet deutlich schneller.
- „Alles prüfen“ zeigt anschließend die tatsächlichen Prüf- und Versionsinformationen an.
- Der Tool-Status in den globalen Einstellungen behält die bestehende Ansicht und ordnet Werkzeuge in Viererblöcken nebeneinander an.
- Die Plugin-Installation zeigt den Fortschritt der Werkzeugprüfung und Einrichtung in einem eigenen Fenster.

## Kompatibilität

- Grundlage für den MediaHub KI-Assistenten v0.4.1 und zukünftige Plugins mit externen Werkzeugen.

Die vollständige Versionshistorie steht in [`CHANGELOG.md`](CHANGELOG.md).

## Start aus dem Quellcode

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Externe Werkzeuge

MediaHub verwendet lokale Werkzeuge wie:

- `yt-dlp.exe`
- `ffmpeg.exe`
- `ffprobe.exe`
- `deno.exe`

Die benötigten Werkzeuge können über das Tool-Center geprüft und teilweise automatisch heruntergeladen werden.

## Wichtige Ordner

```text
config/       Einstellungen, Kanäle und SQLite-Datenbank
downloads/    heruntergeladene Medien
logs/         Protokolle
assets/       Programmbilder und Dokumentation
src/          MediaHub-Quellcode
tools/        externe Werkzeuge
```

## Dokumentation

MediaHub erzeugt beim Release automatisch:

- Kurzanleitung
- Benutzerhandbuch
- Entwicklerhandbuch
- integrierte Hilfe

## Fremdsoftware und Lizenzen

MediaHub verwendet externe Programme, Python-Bibliotheken und optionale Plugin-Werkzeuge. Die Urheberrechte und Lizenzen dieser Bestandteile verbleiben vollständig bei den jeweiligen Projekten und Rechteinhabern. Ein automatischer Download oder die Installation durch MediaHub überträgt keine Rechte an MediaHub.

Die vollständige Übersicht steht in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). Plugins müssen eigene Hinweise für ihre zusätzlichen Bibliotheken, Modelle, Bilder, Sprachdaten und Werkzeuge mitliefern.
