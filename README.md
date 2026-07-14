# MediaHub v1.0.12

MediaHub ist ein lokales PySide6-Programm zum Verwalten von YouTube-Kanälen, Playlists, Video-Downloads, Plex-Importen und separat installierbaren Erweiterungen.

## Neu und verbessert in v1.0.12

### Neu

- Release über den MediaHub Release-Assistenten erstellt.

### Verbessert

- Versions-, Build- und GitHub-Release-Ablauf automatisiert.

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
