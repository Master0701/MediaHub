# MediaHub v1.0.3

MediaHub ist ein lokales PySide6-Programm zum Verwalten von YouTube-Kanälen, Playlists, Video-Downloads, Plex-Importen und Erweiterungen.

## Neu in v1.0.3

- Vorbereitung für die neue MediaHub-Plugin-Erweiterung und zukünftige separat installierbare Plugins.
- Zentrale Versionsverwaltung über `src/mediahub/app_info.py`.
- Installer, EXE-Dateiversion, Handbücher und Release-Pakete übernehmen die Version automatisch.
- Versionierte Download-Dateien für Portable-, Setup- und Handbuch-Pakete.
- Bereinigte offizielle Versionshistorie ohne interne „MediaHub Teil“-Bezeichnungen.

Die vollständige Liste steht in [`CHANGELOG.md`](CHANGELOG.md).

---

# MediaHub v1.0.0-rc10.4

RC10.4 ergänzt den Release Manager im Recovery Center. Damit kann ein sauberes Release-Verzeichnis mit Standardkonfiguration und Release-Bericht vorbereitet werden, ohne die aktuellen privaten Arbeitsdaten zu löschen.

# MediaHub v1.0.0-rc10.4 Final

RC9 bündelt Hilfe-Center, MediaHub-Assistent, Dashboard Pro, Bedienkomfort und eine vorbereitete Plugin-Struktur.

Neu in RC9 Final:
- Plugin Center
- sicheres Plugin-Grundsystem über `plugin.json`
- erstes Startplugin: Bulk Renamer
- Massenumbenennung mit Vorschau, Serien-/Staffel-/Folgen-Platzhaltern und Undo-Log

# MediaHub v1.0.0-rc10.4.4

Neu in rc9.4:
- F1-Kontexthilfe
- F5 aktualisieren
- Strg+B Backup
- Tooltips und „Was ist neu?“
- Keine weitere Dashboard-Überladung

# MediaHub v1.0.0-rc10.4.4

RC9.3 erweitert das Dashboard zur Startzentrale mit Schnellaktionen, Benachrichtigungen und verbessertem Assistentenbereich.


---

## MediaHub v1.0.0-rc10.4.2

Neu in RC9.2:

- MediaHub Assistent als eigene Seite ergänzt
- Health Score mit Prozentanzeige
- automatische Prüfungen für Tools, SQLite-Datenbank, Backups, Scheduler, Downloadordner, Schreibrechte und freien Speicher
- Assistent-Zusammenfassung direkt im Dashboard
- Schnellaktionen für Backup erstellen und Datenbank optimieren
- Version auf v1.0.0-rc10.4.2 gesetzt

# MediaHub v1.0.0-rc10.4

MediaHub ist ein lokales PySide6-Programm zum Verwalten von YouTube-Kanälen, Playlists und Video-Downloads.

## Aktueller Stand

- Kanalverwaltung mit Hinzufügen, Bearbeiten und Löschen
- `config/channels.json` bleibt vorerst die sichere aktive Kanalquelle
- SQLite-Datenbank `config/mediahub.sqlite3` wird jetzt automatisch aufgebaut und synchronisiert
- Kanäle und gespeicherte Playlist-Einstellungen werden beim Start und Speichern in SQLite gespiegelt
- Tabellen für Kanäle, Playlists, Videos, Playlist-Zuordnungen, Downloads und Einstellungen
- Playlists speichern Aktiv-Status, Plex-Name, Staffel, Reihenfolge und Videoanzahl
- Einstellungen werden direkt übernommen
- Tool-Center für externe Werkzeuge
- Prüfung von `yt-dlp` und `ffmpeg`
- Videovorschau für Kanäle
- Videoauswahl vor dem Download
- Playlist-Manager mit dauerhafter Mehr-Playlist-Auswahl
- Kanalstatus im Hauptfenster mit Datenbank-Zahlen zu Playlists, Videos, neuen Videos und letzter Sync
- Download-Warteschlange unten rechts direkt im Hauptfenster
- optionales separates Warteschlangen-Fenster über Toolbar/Menü
- Fortschritt für aktuelles Video und gesamte Warteschlange
- neues Hauptfenster mit linker Navigation und eigenen Seiten für Dashboard, Kanäle, Bibliothek, Downloads, Jobs, Scheduler, Statistik, Health Check, Werkzeuge, Einstellungen, Log und Hilfe
- Downloads ohne Plex-Ziel laufen stabil direkt in den Arbeitsordner
- Job-Queue als Grundlage für Scheduler und Aufgabenketten
- neuer Jobs-Tab unten rechts im Hauptfenster
- Scheduler-Tab mit gespeicherten Sync-Aufgaben
- Scheduler erzeugt kontrolliert Jobs aus fälligen Aufgaben
- Scheduler kann Sync+Auswahl-Aufgaben erzeugen, die nach dem Sync die Videoauswahl öffnen
- Scheduler kann Sync+Auto-Download-Aufgaben erzeugen, die neue Videos direkt in die Download-Warteschlange geben
- Start-Assistent mit Live-Vorschau für Ordnerstruktur und Dateinamenschema
- Wizard mit einklappbarer Platzhalter-Hilfe und „Speichern und Sync starten“
- Health Check mit Prüfung von Datenbank, Tools, Ordnern, Schreibrechten, Scheduler, Job-Queue und Anleitung
- Statistik-Center mit Gesamtzahlen, Zeiträumen, größten Kanälen/Playlists, letzten Downloads und einfachen Balkenlisten

## Start

```powershell
py -m pip install -r requirements.txt
python main.py
```

## Benötigte Tools

Die externen Tools liegen im Ordner `tools`:

- `yt-dlp.exe`
- `ffmpeg.exe`
- `ffprobe.exe`
- `ffplay.exe`

Diese Dateien werden nicht mit Git gespeichert und müssen lokal vorhanden sein.

## Wichtige Ordner

```text
config/      Kanäle und SQLite-Datenbank
logs/        Logdateien
src/         Programmcode
tools/       externe Programme wie yt-dlp und ffmpeg
```

## Datenbank-Hinweis

Ab v0.7.0-alpha wird `config/mediahub.sqlite3` automatisch erstellt. Die JSON-Datei bleibt noch bestehen und wird weiterhin als sichere Hauptquelle benutzt. Ab v0.7.4-alpha werden aktive Playlist-Einstellungen und gefundene Videos zusätzlich in SQLite abgelegt. Die Datenbank dient jetzt als Grundlage für Download-Historie, Dashboard und Scheduler.


## Tools

MediaHub nutzt lokale Tools aus dem Ordner `tools`:

- `yt-dlp.exe`
- `ffmpeg.exe`
- `ffprobe.exe`
- `deno.exe`

Deno wird für die neuere YouTube-Auswertung von yt-dlp vorbereitet und kann über das Tool-Center automatisch heruntergeladen werden.


### v0.7.4-alpha

- Aktive Playlists eines Kanals können gemeinsam über „Videos“ und „Vorschau“ geladen werden.
- Doppelte Videos aus mehreren Playlists werden automatisch gefiltert.


### v0.9.0-alpha

- Dashboard-Grundlage im Hauptfenster ergänzt.
- Neue Manager vorbereitet: DatabaseManager, LibraryManager, StatisticsManager und SchedulerManager.
- Dashboard zeigt Kanäle, Playlists, bekannte Videos, neue Videos, geladene Videos, Mitglieder-Videos, letzte Sync und Datenbankgröße.
- Listen für neue und zuletzt erkannte/synchronisierte Videos ergänzt.
- Bibliothek/Download/Sync bleiben in ihrer bestehenden Logik unverändert.

### v0.8.6-alpha

- Video-Datenbank erweitert: Beschreibung, Thumbnail, Upload-Datum, Dauer, Aufrufe, Downloadstatus, NFO/Thumbnail-Status und Mitglieder-Markierung.
- Neue Tabelle `video_playlists`: Ein Video kann jetzt mehreren Playlists zugeordnet werden, ohne doppelt gespeichert zu werden.
- Synchronisierung aktualisiert Video-Datensätze und Playlist-Zuordnungen.
- SQLite-Schema auf Version 5 erweitert.


### v0.8.0-alpha

- Downloads ohne Plex-Ziel nutzen nun pro Video einen isolierten temporären Arbeitsordner.
- Fertige Dateien werden anschließend sauber in den Kanal-Arbeitsordner verschoben.
- Dadurch sollen alte Sidecar-Dateien und liegengebliebene `.part`-Dateien den nächsten Queue-Download nicht mehr stören.


### v0.9.2-alpha

- Job-Queue-Grundlage ergänzt.
- SQLite-Tabelle `jobs` vorbereitet.
- Scheduler ist jetzt als Job-Erzeuger vorbereitet, führt aber noch keine automatischen Hintergrundläufe aus.

## Hilfe und Dokumentation

- PDF-Anleitung: `docs/MediaHub_Anleitung.pdf`
- Hilfe-Menü mit Anleitung, Erste Schritte, Changelog, Log-Ordner, Systeminformationen, Health Check und Über MediaHub
- Über-Dialog mit Projektidee: Shadow1racer, Programmdesign und Entwicklung: Master2511, KI-Unterstützung: ChatGPT (OpenAI)


### Recovery Center (rc8)

MediaHub besitzt jetzt ein Recovery Center. Dort können ZIP-Backups mit manifest.json erstellt, vorhandene Backups geprüft, gelöscht und config-Dateien sicher wiederhergestellt werden. Vor einer Wiederherstellung legt MediaHub automatisch eine Sicherheitskopie der aktuellen config an.


### Recovery Center / Backups

Das Recovery Center kann ZIP-Backups mit `manifest.json` erstellen, vorhandene Backups anzeigen, Konfigurationsdaten wiederherstellen und Wartungsfunktionen ausführen. Zusätzlich können automatische Backups geplant werden; diese erscheinen als Backup-Aufgaben im Scheduler.

Wartungsfunktionen in rc8:

- Datenbank prüfen
- Datenbank bereinigen
- Datenbank optimieren / VACUUM
- verwaiste Downloads suchen
- Archiv-/Downloadordner prüfen

## v1.0.0-rc8_settingsfix

- Einstellungen-Seite ersetzt den Platzhalter durch echte globale Optionen.
- Ordnerpfade, Download-Defaults, Plex-Defaults, Backup-Vorgaben und Tool-Status ergänzt.
- Einstellungen werden in `config/settings.json` gespeichert.


## v1.0.0-rc10.4

Neu in rc9:

- Hilfe-Center direkt im Programm
- Suche nach Hilfethemen
- Schnellzugriffe in passende Programmbereiche
- PDF-Handbuch unter `docs/MediaHub_Anleitung.pdf`
- MediaHub-Assistent für Health Check, Recovery und Einstellungen



## Stand: RC10.2

RC10 startet den Release-Feinschliff. In diesem Schritt wurden keine grossen neuen Funktionen eingebaut, sondern UI-Standards, Lesbarkeit und Plugin/Bulk-Renamer-Layout verbessert.


## RC10.2

- Schnellaktionen wieder lesbar wie in RC9.3.
- Was ist neu? erscheint nur einmal pro Version.
- Hilfe-Center enthält eine Versionshistorie aus CHANGELOG.md.


## Selbsttest

Ab rc10.3 kann MediaHub automatisch geprueft werden:

```bash
python tools/mediahub_selftest.py --mode quick
python tools/mediahub_selftest.py --mode full
python tools/mediahub_selftest.py --mode release
```

Die Berichte werden unter `logs/` als TXT und HTML gespeichert.


## RC10.5

Dieses Paket enthält den Release Builder. Über das Recovery Center kann ein sauberes Release-Verzeichnis und ein Release-ZIP erstellt werden. Zusätzlich liegen Build-Hinweise für PyInstaller im Ordner `build/`.
