# MediaHub v1.0.13

MediaHub ist ein lokales PySide6-Programm zum Verwalten von YouTube-Kanälen, Playlists, Video-Downloads, Plex-Importen und separat installierbaren Erweiterungen.

## Neu und verbessert in v1.0.13

## Plugin-Verwaltung für WebRemote und Mobile Dashboard

- MediaHub stellt kontrollierte Plugin-Aktionen für Starten, Stoppen, Aktivieren, Deaktivieren, Installieren und Entfernen bereit.
- Die Plugin-API liefert den echten Laufstatus sowie freigegebene Weboberflächen.
- WebRemote und Mobile Dashboard können zusätzliche Plugin-Weboberflächen in einem neuen Browser-Tab öffnen.
- Reine Web-Shells und Hintergrund-Plugins werden nicht als Plugin-Oberflächen angeboten.
- UTF-8-Verarbeitung bleibt für Manifest- und Plugin-Dateien erhalten.

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
