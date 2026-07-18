# Ausstehende Release-Notizen

## MediaHub – Tool-Manager und Tool-Assistent vollständig ausgebaut

### Neuer Tool-Manager

- Zentrales Datenmodell für MediaHub- und Plugin-Werkzeuge eingeführt.
- Status, Version, Lizenz, Homepage, Installationsquelle und Nutzung werden einheitlich angezeigt.
- Filter für MediaHub-Tools, Plugin-Tools, installierte, fehlende, benötigte, optionale und unbenutzte Werkzeuge ergänzt.
- Tool-Karten und Gesamtübersicht im Tool-Center neu aufgebaut.

### Plugin-Integration

- Aktivierte Plugins melden Pflicht- und optionale Werkzeuge automatisch an.
- Deaktivierte oder entfernte Plugins werden unmittelbar aus der Tool-Nutzung entfernt.
- Änderungen werden ohne Neustart im geöffneten Tool-Center aktualisiert.
- Fehlende Plugin-Pflichttools werden portabel im MediaHub-Ordner `tools/` installiert.

### Installation und Updates

- Installationsquelle und Versionsstatus für Werkzeuge ergänzt.
- Einzelne und gemeinsame Update-Prüfung eingeführt.
- Sichere Neuinstallation und Aktualisierung für yt-dlp und Deno umgesetzt.
- Vor dem Austausch wird eine Sicherung angelegt.
- Bei Fehlern wird automatisch auf die vorherige Version zurückgerollt.
- MediaInfo wird bei der Statusprüfung nicht mehr unbeabsichtigt als GUI gestartet.

### Tool-Assistent

- Neuer Tool-Assistent mit Gesamtstatus, Sammelprüfung, Installation fehlender Pflichttools und sicheren Sammelupdates.
- Unter „Werkzeuge“ wurde nur der alte Menüpunkt „Tools prüfen“ durch „Tool-Assistent“ ersetzt.
- Die Einzelprüfung „Tools prüfen“ im Tool-Center bleibt erhalten.
- Die automatische Pflichttool-Prüfung beim Programmstart bleibt aktiv.
- Der Release-Assistent des Hauptprogramms wurde funktional nicht zum Tool-Assistenten umgebaut.

### Lizenzen und Release-Sicherheit

- Zentrale Datei `THIRD_PARTY_LICENSES.md` ergänzt.
- Ordner `licenses/` mit den benötigten Standard-Lizenztexten ergänzt.
- Installer, Portable-Paket, Build und Release-Vorbereitung übernehmen Lizenzübersicht und Lizenzordner.
- Release-Assistent und Veröffentlichungs-Skript blockieren ein Release, wenn Pflicht-Lizenzdateien fehlen oder leer sind.
- `.gitignore` um Arbeits-, Download-, Cache-, Backup- und temporäre Ordner des Tool-Managers erweitert.
- Beschädigte Unicode-Dateinamen der Dokumentation korrigiert.
- Dokumentations-Loader für ausdrücklich gesetzte Basisordner korrigiert.

## Commit-Nachricht

Tool-Manager, Tool-Assistent und Lizenzprüfung vervollständigen

## Tool-Assistent – Installation fehlender Pflichttools korrigiert

- Der Tool-Assistent richtet jetzt sowohl fehlende MediaHub-Kernwerkzeuge als auch Plugin-Pflichttools ein.
- yt-dlp, FFmpeg, FFprobe und Deno werden über die vorhandenen offiziellen MediaHub-Downloadquellen installiert.
- Plugin-Pflichttools werden anschließend aus den hinterlegten Downloadquellen portabel unter `tools/<werkzeug>/` installiert.
- Vor der Installation zeigt der Assistent die konkrete Liste der fehlenden Pflichttools an.
- Nach dem Vorgang werden weiterhin fehlende Werkzeuge verständlich aufgelistet; die irreführende Meldung „0 Pflichttools eingerichtet“ entfällt.


## Phase 6.5 – Portabler Tool-Manager

- Sämtliche MediaHub- und Plugin-Werkzeuge werden ausschließlich im MediaHub-Ordner `tools/` verwaltet.
- Für jedes Werkzeug wird ein eigener Unterordner verwendet, beispielsweise `tools/ffmpeg/`, `tools/mediainfo/` und `tools/mkvtoolnix/`.
- Systemweite Installationen unter `C:\Program Files` und die Installation über WinGet werden nicht mehr verwendet.
- Alte lose Dateien wie `tools/ffmpeg.exe` werden beim ersten Start automatisch in die neue Struktur übernommen und anschließend aus dem alten Ablageort entfernt.
- Die zentrale Pfadauflösung unterstützt während der Migration weiterhin alte Installationen, bevorzugt aber immer die neue portable Struktur.
- Download-Service, Deno-Laufzeit, FFmpeg-Suche, Gesundheitsprüfung, Tool-Center und Plugins verwenden dieselbe zentrale Pfadauflösung.
- Jede eingerichtete Tool-Gruppe erhält eine `manifest.json` mit Version, Quelle, Lizenz, Installationszeitpunkt und relativem Programmpfad.
- MediaInfo wird aus dem offiziellen GitHub-Release als portable CLI-ZIP geladen.
- MKVToolNix wird aus der offiziellen Downloadquelle direkt in den MediaHub-Toolordner eingerichtet.
- Tesseract wird über den in der offiziellen Tesseract-Dokumentation empfohlenen Windows-Build von UB Mannheim in den MediaHub-Toolordner eingerichtet.
- Neuinstallation und Aktualisierung sichern vorhandene Plugin-Werkzeugordner und stellen sie bei Fehlern automatisch wieder her.
- Neue Tests prüfen die bevorzugte Ordnerstruktur, die automatische Migration und das Verbot eines Rückfalls auf systemweite Programmordner.
