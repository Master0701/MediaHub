# MediaHub v1.0.14

MediaHub ist ein lokales PySide6-Programm zum Verwalten von YouTube-Kanälen, Playlists, Video-Downloads, Plex-Importen und separat installierbaren Erweiterungen.

## Neu und verbessert in v1.0.14

# Ausstehende Release-Notizen

## MediaHub v1.0.14

### Neu

- Zentrale Fremdsoftware- und Lizenzübersicht für MediaHub, Plugins und zusätzliche Werkzeuge ergänzt.
- Neues Kapitel **Lizenzen und Fremdsoftware** in das integrierte Hilfe-Center aufgenommen.
- Plugin-Manifeste unterstützen jetzt `required_tools` und `optional_tools`.
- Der zentrale ToolService erfasst, welche installierten Plugins ein Werkzeug zwingend oder optional verwenden.

### Verbessert

- Der Menüpunkt **Hilfe → Lizenzen und Fremdsoftware** öffnet nun eine normale TXT-Datei statt einer Markdown-Datei und wird dadurch nicht mehr automatisch in VS Code geöffnet.
- Plugin Center und ToolService wurden verbunden, sodass Werkzeugabhängigkeiten beim Laden, Installieren und Entfernen von Plugins automatisch neu registriert werden.
- Installer, Portable-Paket und Release-Paket übernehmen die Fremdsoftware-Hinweise.
- README, Über-Dialog und Entwicklerdokumentation wurden um klare Lizenzhinweise erweitert.
- Release-Dateien werden weiterhin aus der zentralen MediaHub-Version erzeugt.

### Technischer Hinweis

- Die automatische Installation fehlender Plugin-Werkzeuge wird in einem folgenden Entwicklungsschritt ergänzt. Die Erkennung und zentrale Zuordnung sind bereits vorbereitet.

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
