# Recovery Center

## Einführung

Das Recovery Center ist die zentrale Anlaufstelle für Wartung, Sicherung und Fehlerbehebung.

Hier können Backups erstellt, Wiederherstellungen durchgeführt und der Zustand der MediaHub-Installation überprüft werden.

![Recovery Center](images/10_recovery.png)

---

# Aufgaben des Recovery Centers

Das Recovery Center unterstützt unter anderem bei:

- Erstellen von Backups
- Wiederherstellen von Sicherungen
- Überprüfung wichtiger Dateien
- Kontrolle der Datenbank
- Analyse von Fehlern
- Wartungsarbeiten

Dadurch lassen sich viele Probleme beheben, ohne Dateien manuell bearbeiten zu müssen.

---

# Backups erstellen

MediaHub kann wichtige Daten automatisch sichern.

Dazu gehören beispielsweise:

- Datenbank
- Einstellungen
- Kanäle
- Scheduler-Aufgaben
- Plugins
- Dokumentation

Backups können jederzeit erstellt werden.

Vor größeren Änderungen empfiehlt sich grundsätzlich eine Sicherung.

---

# Wiederherstellung

Ein vorhandenes Backup kann vollständig wiederhergestellt werden.

Dabei werden die gesicherten Daten zurück in die MediaHub-Installation übernommen.

Nach der Wiederherstellung empfiehlt sich ein Neustart von MediaHub.

---

# Selbsttest

Der integrierte Selbsttest überprüft automatisch die wichtigsten Komponenten.

Unter anderem werden kontrolliert:

- Datenbank
- Ordnerstruktur
- Schreibrechte
- Werkzeuge
- Dokumentation
- Plugins

Gefundene Probleme werden direkt angezeigt.

---

# Datenbankprüfung

Die Datenbank enthält sämtliche Informationen über:

- Kanäle
- Videos
- Downloads
- Playlists
- Scheduler
- Jobs

Bei einer Prüfung kontrolliert MediaHub die Konsistenz dieser Daten.

---

# Logdateien

Alle wichtigen Ereignisse werden automatisch protokolliert.

Dazu gehören:

- Downloads
- Synchronisierungen
- Fehler
- Warnungen
- Systemmeldungen

Die Logdateien erleichtern die Fehlersuche erheblich.

---

# Wartung

Das Recovery Center unterstützt verschiedene Wartungsaufgaben.

Beispiele:

- temporäre Dateien entfernen
- Datenbank prüfen
- Backups verwalten
- Systeminformationen anzeigen

---

# Tipps

💡 Erstelle regelmäßig Backups.

Besonders vor größeren Änderungen oder Updates.

---

💡 Hebe mehrere ältere Sicherungen auf.

Dadurch kann bei Bedarf auch auf ältere Stände zurückgegriffen werden.

---

# Hinweise

⚠ Während einer Wiederherstellung sollte MediaHub nicht beendet werden.

---

⚠ Eine Wiederherstellung ersetzt vorhandene Daten durch die Inhalte des Backups.

---

# Häufige Probleme

## Backup kann nicht erstellt werden

Prüfen:

- Schreibrechte
- freier Speicherplatz
- Zielordner vorhanden

---

## Wiederherstellung schlägt fehl

Prüfen:

- Backup vollständig?
- Backup beschädigt?
- ausreichend Speicherplatz vorhanden?

---

## Datenbankfehler

Führe zunächst den Selbsttest aus.

Anschließend kann die Datenbankprüfung gestartet werden.

---

# Siehe auch

- Health Check
- Einstellungen
- Scheduler
- Logdateien
- Hilfe