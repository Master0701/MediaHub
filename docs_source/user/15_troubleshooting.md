# Fehlerbehebung

## Einführung

Trotz sorgfältiger Entwicklung können gelegentlich Probleme auftreten.

Dieses Kapitel hilft dabei, typische Fehler schnell zu erkennen und zu beheben.

---

# MediaHub startet nicht

Prüfe:

- Python korrekt installiert?
- Alle benötigten Dateien vorhanden?
- Fehlermeldungen im Terminal beachten.

Falls nötig, stelle die letzte Sicherung über das Recovery Center wieder her.

---

# Keine Videos gefunden

Kontrolliere:

- Kanal-URL
- Internetverbindung
- Synchronisierung durchgeführt
- Kanal öffentlich erreichbar

---

# Downloads funktionieren nicht

Prüfe:

- yt-dlp installiert
- FFmpeg installiert
- Downloadordner vorhanden
- Schreibrechte vorhanden

Führe anschließend den Health Check aus.

---

# Scheduler arbeitet nicht

Prüfe:

- Scheduler aktiviert
- Aufgabe aktiviert
- Uhrzeit korrekt
- Job-Queue aktiv

---

# Datenbankfehler

Starte zunächst den Health Check.

Bleibt der Fehler bestehen:

1. Backup erstellen.
2. Recovery Center öffnen.
3. Datenbank überprüfen.

---

# Dokumentation fehlt

Falls Handbuch oder Hilfe fehlen:

```text
python build_docs.py
```

Dadurch werden sämtliche Dokumente neu erzeugt.

---

# Plugins werden nicht erkannt

Prüfe:

- Plugin im richtigen Ordner?
- plugin.json vorhanden?
- Plugin vollständig installiert?

---

# Logdateien

Bei Problemen lohnt sich immer ein Blick in die Logdateien.

Dort werden Fehler und Warnungen protokolliert.

---

# Support

Sollte ein Problem weiterhin bestehen:

- Health Check ausführen
- Logdateien prüfen
- Recovery Center verwenden
- Dokumentation durchsuchen

Viele Probleme lassen sich bereits mit diesen Schritten beheben.

---

# Tipps

💡 Vor größeren Änderungen immer ein Backup erstellen.

---

💡 Nach Updates einmal den Health Check ausführen.

---

💡 Die Dokumentation regelmäßig mit

```text
python build_docs.py
```

aktualisieren.

---

# Siehe auch

- FAQ
- Recovery Center
- Health Check
- Hilfe-Center