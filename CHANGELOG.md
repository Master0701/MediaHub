# Changelog

## v1.0.7

### Neu

- Release über den MediaHub Release-Assistenten erstellt.

### Verbessert

- Versions-, Build- und GitHub-Release-Ablauf automatisiert.

## v1.0.6

### Neu

- Release über den MediaHub Release-Assistenten erstellt.

### Verbessert

- Versions-, Build- und GitHub-Release-Ablauf automatisiert.

## v1.0.5

# Änderungen

## Behoben

- API-Anbindung zwischen MediaHub und den Plugins korrigiert.
- Interne MediaHub-API für die weitere Plugin-Entwicklung stabilisiert.
- Kompatibilität mit dem aktuellen Stand von `MediaHub_Plugins` verbessert.

## Hinweise

- Nach diesem API-Fix sollte die MediaHub-Version als Patch-Version erhöht werden.
- Plugin-Kompatibilitätsangaben wie `minimum_mediahub` müssen zur neuen MediaHub-Version passen.

## v1.0.4

### Neu

- Release über den MediaHub Release-Assistenten erstellt.

### Verbessert

- Versions-, Build- und GitHub-Release-Ablauf automatisiert.

## v1.0.3 – Plugin-Erweiterung und zentrale Versionsverwaltung

### Neu

- MediaHub für die neue Plugin-Erweiterung und zukünftige separat installierbare Plugins vorbereitet.
- Release-Dateien erhalten ihre Versionsnummer jetzt automatisch aus einer zentralen Quelle.
- Portable-, Setup- und Handbuch-Pakete werden direkt mit der aktuellen Versionsnummer benannt.

### Verbessert

- `src/mediahub/app_info.py` ist jetzt die einzige manuell gepflegte Versionsquelle.
- EXE-Dateiversion und Installer-Definition werden vor jedem Build automatisch erzeugt.
- Programmfenster, „Was ist neu?“, Dokumentation und Release-Build verwenden dieselbe Version.
- GitHub-Release-Workflow übernimmt die bereits korrekt benannten Download-Dateien ohne nachträgliches Umbenennen.

### Hinweise

- Der vorhandene Passwortschutz des Release-Assistenten bleibt unverändert und abgeschlossen.
- Interne Arbeitsbezeichnungen wie „MediaHub Teil 10“ wurden aus den offiziellen Release-Einträgen entfernt.

## v1.0.1

### Fehlerbehebungen

- „Ordner öffnen“ in der Bibliothek repariert.
- Bereits heruntergeladene Videos werden lokal statt erneut auf YouTube geöffnet.
- Erfolgreiche Downloads werden zuverlässig in SQLite als geladen gespeichert.
- Fehlende Video-Datensätze werden nach einem Download automatisch angelegt.
- Der endgültige lokale Dateipfad wird auch nach dem Plex-Import gespeichert.
- Videos im Standard-Arbeitsordner werden ebenfalls korrekt in der Datenbank erfasst.
- Die Bibliothek wird beim Wechsel zwischen Dashboard und Bibliothek nicht mehr unnötig neu geladen.
- Der Kanalbereich wurde verbreitert; das rechte Einstellungsfenster kann kompakter dargestellt werden.
- Kanalinformationen besitzen jetzt einen vertikalen Scrollbereich und bleiben vollständig erreichbar.

### Verbesserungen

- Bibliotheksabfragen und Playlist-Zuordnungen wurden durch zusätzliche SQLite-Indizes vorbereitet.
- Lange Pfade in den Kanaleinstellungen können sauber umbrechen.
- Datenbank- und Bibliotheksaktualisierung nach abgeschlossenen Downloads verbessert.
- Kanal- und Datenbankstatus bleiben auch bei kleineren Fensterhöhen vollständig bedienbar.

## v1.0.0-rc10.5

- Release Builder ergänzt.
- Release-ZIP-Erstellung im Recovery Center ergänzt.
- Build-Dateien für PyInstaller vorbereitet (`build/MediaHub.spec`, `build/build_exe.bat`).
- Release-Bericht um ZIP-Informationen erweitert.
- Abschluss vor MediaHub v1.0.0 vorbereitet.

# Changelog

## v1.0.0-rc10.4

- Release Manager im Recovery Center ergänzt.
- Sichere Release-Vorbereitung als separates `release_ready/`-Verzeichnis.
- Standardkonfiguration ohne private Daten erzeugbar.
- Release-Bericht als TXT/HTML unter `logs/`.
- Bereinigungs-Trockenlauf für Logs, Downloads, Backups und Cache ergänzt.

## v1.0.0-rc10.3

### Neu
- MediaHub Selbsttest als Konsolenscript unter `tools/mediahub_selftest.py`.
- Schnelltest, Volltest und Release-Test im Recovery Center.
- Automatische Text- und HTML-Berichte unter `logs/`.
- Plugin-API um `register_test`, `register_menu`, `register_panel` und `register_settings` vorbereitet.

### Qualität
- Selbsttest prueft Projektstruktur, Datenbank, Einstellungen, Ordner, Recovery, Scheduler, Plugins und Hilfe-Dateien.
- Release-Test liefert am Ende eine klare Freigabe: `READY FOR RELEASE`, wenn keine Fehler gefunden wurden.

## MediaHub v1.0.0-rc10.1

## v1.0.0-rc10.2

- Schnellaktionen wieder auf den gut lesbaren RC9.3-Stand zurückgesetzt.
- Was-ist-neu-Fenster auf aktuelle Versionsänderungen reduziert.
- Was-ist-neu-Fenster erscheint nur einmal pro Version über config/ui_state.json.
- Hilfe-Center um Versionshistorie erweitert.
- Versionshistorie liest CHANGELOG.md als zentrale Quelle.


- RC10-Feinschliff gestartet.
- Version auf v1.0.0-rc10.1 gesetzt.
- Gemeinsame UI-Standards fuer Buttonhoehen, Panel-Abstaende und Titel ergaenzt.
- Plugin Center Layout entzerrt und besser lesbar gemacht.
- Bulk Renamer Layout mit Scrollbereich und groesserer Vorschautabelle verbessert.
- Dunkles Theme leicht vereinheitlicht.
- Keine neuen Dashboard-Inhalte ergaenzt.

## MediaHub v1.0.0-rc9 Final

- RC9.1 bis RC9.4 zusammengeführt.
- Plugin-Grundsystem ergänzt (`plugins/`, Manifest-Lader, Plugin Center).
- Bulk Renamer als erstes sicheres Startplugin ergänzt.
- Bulk Renamer kann Ordner/Dateien per Vorschau massenhaft umbenennen.
- Platzhalter für Serie, Staffel, Folge, Index und Datum ergänzt.
- Undo-Log für Umbenennungen ergänzt.
- Dashboard bleibt unverändert, damit es nicht überladen wird.
- Version auf v1.0.0-rc9 gesetzt.

## MediaHub v1.0.0-rc9.4

Neu:
- F1-Kontexthilfe für die aktuelle Seite
- F5 aktualisiert die sichtbare Seite
- Strg+B erstellt ein Backup über den Assistenten
- Tooltips für Navigation, Statusleiste und wichtige Aktionen
- „Was ist neu?“-Dialog pro Version
- Dashboard bleibt bewusst unverändert/kompakt
- Version auf v1.0.0-rc9.4 gesetzt

## MediaHub v1.0.0-rc9.3

Neu in RC9.3:

- Dashboard Pro ergänzt
- Schnellaktionen direkt auf dem Dashboard
- Benachrichtigungsbereich für Assistent-Warnungen
- Health Score jetzt mit Fortschrittsbalken
- Assistent-Karte auf dem Dashboard übersichtlicher gemacht
- Backup-Schnellaktion mit Wechsel ins Recovery Center
- Version auf v1.0.0-rc9.3 gesetzt

## MediaHub v1.0.0-rc9.2

Neu in RC9.2:

- MediaHub Assistent als eigene Seite ergänzt
- Health Score mit Prozentanzeige
- automatische Prüfungen für Tools, SQLite-Datenbank, Backups, Scheduler, Downloadordner, Schreibrechte und freien Speicher
- Assistent-Zusammenfassung direkt im Dashboard
- Schnellaktionen für Backup erstellen und Datenbank optimieren
- Version auf v1.0.0-rc9.2 gesetzt

# Changelog

## v1.0.0-rc9

- Hilfe-Center als eigene Hauptseite ergänzt.
- Suchfunktion für Hilfethemen eingebaut.
- Schnellzugriffe zu Kanälen, Playlists, Downloads, Bibliothek, Scheduler, Recovery Center, Einstellungen, Tool Center und Health Check ergänzt.
- PDF-Handbuch über Hilfe-Center und Hilfe-Menü erreichbar.
- MediaHub-Assistent mit direkten Problemlösungs-Buttons ergänzt.
- Benutzerhandbuch unter docs/MediaHub_Anleitung.pdf aktualisiert.


## v1.0.0-rc8

- Recovery Center als neue Hauptseite ergänzt.
- Backup-Service mit ZIP-Backups und manifest.json eingebaut.
- Backup-Liste mit Detailansicht, Größe, Version, Inhalt und Kommentar ergänzt.
- Sichere Wiederherstellung für config-Dateien mit automatischer Sicherheitskopie vor Restore ergänzt.
- Backup löschen und Backup-Ordner öffnen ergänzt.

## v1.0.0-rc7

- Statistik-Center ersetzt den bisherigen Platzhalter.
- Gesamtübersicht für Kanäle, Playlists, Videos, Downloads, neue Videos, Mitglieder-Videos, Downloadquote, Fehlerquote, Datenbankgröße und Downloadordnergröße ergänzt.
- Zeiträume für heute, diese Woche und diesen Monat ergänzt.
- Größte Kanäle, größte Playlists, letzte Downloads, Downloads pro Tag und neue Videos pro Woche ergänzt.
- Statistik wird beim Öffnen der Statistik-Seite und nach Job-Aktualisierungen erneuert.

## v1.0.0-rc5

- Health Check als eigene Seite in der linken Navigation ergänzt.
- Prüfung für SQLite/Repository, Datenbankdatei, yt-dlp, FFmpeg, FFprobe, Deno, Ordner, Schreibrechte, Scheduler, Job-Queue und Anleitung erweitert.
- Health Check legt fehlende Standardordner nach Möglichkeit automatisch an und zeigt klare Hinweise.
- Hilfe- und Werkzeuge-Seite verlinken jetzt direkt zur Health-Check-Seite.

## v1.0.0-rc4

- Bibliothekssuche entkoppelt: Suchabfragen laufen jetzt im Hintergrund.
- Suche startet verzögert nach dem Tippen statt bei jedem Buchstaben sofort.
- Trefferlimit bei Such-/Filterabfragen reduziert, damit die Oberfläche reaktionsfähig bleibt.
- Aktualisieren-Button bleibt während laufender Suche gesperrt.

## v1.0.0-rc2

- Bibliothek öffnet schneller und blockiert das Hauptfenster weniger.
- Beim Öffnen der Bibliothek erscheint jetzt eine Ladeanzeige.
- Bibliothek lädt initial nur die ersten 250 Einträge; Suche/Filter laden bis zu 500 Einträge.
- Tabellenaktualisierung der Bibliothek wurde gepuffert und flackerärmer gemacht.

## v1.0.0-rc1

- Release-Candidate-Oberfläche mit linker Navigation eingeführt.
- Hauptbereiche jetzt als Seiten: Dashboard, Kanäle, Bibliothek, Downloads, Jobs, Scheduler, Statistik, Werkzeuge, Einstellungen, Log und Hilfe.
- Hilfe-Menü erweitert: Anleitung, Erste Schritte, Changelog, Log-Ordner, Systeminformationen, Health Check und Über MediaHub.
- Neuer Über-Dialog mit Projektidee, Programmdesign/Entwicklung und KI-Unterstützung.
- Erste PDF-Anleitung unter `docs/MediaHub_Anleitung.pdf` ergänzt.
- Health-Check-Grundlage für SQLite, Tools und Schreibrechte ergänzt.

## v0.9.9.3-alpha

- Automation-Schritt 2: neuer Job-Typ **Sync+Auto-Download**.
- Scheduler kann jetzt Aufgaben anlegen, die nach dem Sync neue Videos automatisch in die Download-Warteschlange geben.
- Scheduler-Tab unterscheidet jetzt **Sync+Auswahl** und **Auto-Download**.
- Auto-Download überspringt Mitglieder-Videos und nutzt weiter den stabilen DownloadManager-Pfad.

## v0.9.9.3-alpha

- Hotfix: Wizard-Button „Speichern und starten“ startet jetzt zuverlässig den Ablauf.
- Wizard setzt jetzt sicher Sync + Download-Auswahl nach dem Speichern.
- Wizard-Seite 3 weiter entzerrt: Optionen sind einklappbar.

## v0.9.9.3-alpha

- Wizard-Seite 3 weiter entzerrt.
- Poster/Fanart in einklappbaren Bereich verschoben.
- Optionen kompakter angeordnet.
- Wizard kann nach dem Speichern synchronisieren und danach neue Videos zur Download-Auswahl öffnen.
- Klarer Hinweis: Ordner entstehen erst beim bestätigten Download.

# v0.9.9.3-alpha

- Hotfix: Start-Assistent öffnet wieder.
- Fehlende Methode für „Speichern und Sync starten“ ergänzt.

# Changelog

## v0.9.9.3-alpha

- Wizard-Seite 3 luftiger gestaltet.
- Platzhalter-Hilfe einklappbar gemacht.
- Custom-Button **Speichern und Sync starten** ergänzt.
- Zusammenfassung im Wizard klarer beschriftet.
- Wizard erklärt jetzt besser, dass Ordner erst beim echten Download entstehen.

## v0.9.7-alpha

- Start-Assistent verbessert.
- Live-Vorschau für Playlist-Ordnerstruktur ergänzt.
- Live-Vorschau für Dateinamenschema ergänzt.
- Kurzbeschreibungen für Platzhalter und Beispiel-Ausgabe erweitert.

## v0.9.5-alpha

- Scheduler-Automatik ergänzt.
- Scheduler prüft fällige Aufgaben automatisch im 60-Sekunden-Takt.
- Fällige Aufgaben erzeugen weiterhin Jobs über die Job-Queue.
- Optionaler Sofort-Check im Scheduler-Tab.
- Automatik kann im Scheduler-Tab pausiert/aktiviert werden.

## v0.9.3-alpha

- Erster echter Scheduler-Baustein ergänzt.
- Neuer Tab **Scheduler** unten rechts im Hauptfenster.
- Neue SQLite-Tabelle `scheduled_tasks`.
- Sync-Aufgaben können für den aktuellen Kanal gespeichert werden.
- Fällige Scheduler-Aufgaben erzeugen Jobs in der Job-Queue.
- Ausgewählte Scheduler-Aufgaben können sofort als Job erzeugt werden.

## v0.9.2-alpha

- Job-Engine aktiv.
- Jobs können manuell gestartet werden.
- Sync-Jobs laufen über die Job-Queue.
- Job-Status: wartet / läuft / fertig / Fehler.

## v0.9.1-alpha

- Job-Queue-Grundlage ergänzt.
- Neuer Tab **Jobs**.
- SQLite-Tabelle `jobs` ergänzt.
- Scheduler an Job-Queue vorbereitet.

## v0.9.0-alpha

- Dashboard im Hauptfenster ergänzt.
- Globale Übersicht für Kanäle, Playlists, Videos, neue Videos, geladene Videos und Mitglieder-Videos.
- Manager für Datenbank, Bibliothek, Statistik und Scheduler vorbereitet.

## v0.8.6-alpha

- Bibliothek 2.0 ergänzt.
- Rechtsklick-Menü für Videoeinträge.
- Doppelklick öffnet lokale Datei oder YouTube.
- Status-Icons ergänzt.

## v0.8.5-alpha

- Bibliothek mit Detailbereich ergänzt.

## v0.8.4-alpha

- Bibliothek im Hauptfenster ergänzt.
- Suche und Filter für SQLite-Videodatenbank.

## v0.8.3-alpha

- Kanalstatus im linken Hauptfenster ergänzt.

## v0.8.2-alpha

- Queue-Fenster öffnet automatisch beim Downloadstart.

## v0.8.1-alpha

- Video-Datenbank erweitert.
- Tabelle `video_playlists` ergänzt.

## v0.8.0-alpha

- Erste Kanal-Synchronisation ergänzt.


## v1.0.0-rc8 Ergänzung

- Recovery Center erweitert: aktive Wartungsfunktionen statt Platzhalter.
- Datenbankprüfung mit SQLite `PRAGMA integrity_check`.
- Datenbankpflege und Optimierung mit `PRAGMA optimize` und `VACUUM`.
- Archiv-/Downloadordner-Prüfung ergänzt.
- Suche nach möglichen verwaisten Download-Dateien ergänzt.
- Automatische Backups können im Recovery Center als Scheduler-Aufgabe angelegt werden.
- Scheduler kann Backup-Aufgaben ausführen und erstellt dabei ZIP-Backups mit Manifest.

## v1.0.0-rc8 Layout-Fix
- Recovery Center Layout repariert.
- Linke Wartungs-/Backup-Seite in Scrollbereich gelegt.
- Buttons bekommen feste Mindesthöhe und werden nicht mehr unlesbar zusammengeschoben.
- Backup-Liste, Details und Protokoll mit sinnvolleren Mindestgrößen versehen.

## v1.0.0-rc8_settingsfix

- Einstellungen-Seite ersetzt den Platzhalter durch echte globale Optionen.
- Ordnerpfade, Download-Defaults, Plex-Defaults, Backup-Vorgaben und Tool-Status ergänzt.
- Einstellungen werden in `config/settings.json` gespeichert.

