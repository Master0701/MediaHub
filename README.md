# MediaHub v1.0.5

MediaHub ist ein lokales PySide6-Programm zum Verwalten von YouTube-Kanälen, Playlists, Video-Downloads, Plex-Importen und separat installierbaren Erweiterungen.

## Neu und verbessert in v1.0.5

- API-Anbindung zwischen MediaHub und den Plugins korrigiert.
- Interne MediaHub-API für die weitere Plugin-Entwicklung stabilisiert.
- Kompatibilität mit dem aktuellen Stand von `MediaHub_Plugins` verbessert.
- Zentrale Versionsverwaltung über `src/mediahub/app_info.py`.
- Automatisierter Build-, Git-, Tag- und GitHub-Release-Ablauf.
- Release-Notizen werden über `RELEASE_NOTES_PENDING.md` verarbeitet.

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
