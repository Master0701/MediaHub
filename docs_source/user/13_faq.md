# FAQ

## Einführung

In diesem Kapitel werden häufig gestellte Fragen zu MediaHub beantwortet.

Viele Probleme lassen sich dadurch schnell lösen, ohne lange nach der Ursache suchen zu müssen.

---

# Warum werden keine Videos gefunden?

Prüfe folgende Punkte:

- Ist die Kanal-URL korrekt?
- Besteht eine Internetverbindung?
- Wurde der Kanal bereits synchronisiert?
- Ist der Kanal öffentlich erreichbar?

---

# Warum startet kein Download?

Kontrolliere:

- yt-dlp installiert
- FFmpeg installiert
- Downloadordner vorhanden
- Schreibrechte vorhanden

Führe anschließend den **Health Check** aus.

---

# Warum werden Videos übersprungen?

Mögliche Ursachen:

- Video wurde bereits heruntergeladen.
- Video befindet sich bereits in der Datenbank.
- Mitglieder-Video ohne Berechtigung.
- Playlist wurde deaktiviert.

---

# Kann ich mehrere Kanäle gleichzeitig verwalten?

Ja.

MediaHub wurde genau dafür entwickelt.

Jeder Kanal besitzt:

- eigene Einstellungen
- eigene Playlists
- eigene Downloadordner
- eigene Synchronisierung
- eigene Archivinformationen

---

# Muss ich nach jeder Synchronisierung alle Videos herunterladen?

Nein.

Nach jeder Synchronisierung kannst du auswählen:

- alle Videos
- einzelne Videos
- gar keine Videos

Oder du verwendest den Auto-Download.

---

# Was passiert bei einem Programmabsturz?

Beim nächsten Start bleiben erhalten:

- Datenbank
- Kanäle
- Einstellungen
- heruntergeladene Videos

Nicht vollständig heruntergeladene Dateien müssen eventuell erneut geladen werden.

---

# Kann ich MediaHub ohne Scheduler benutzen?

Ja.

Alle Funktionen können auch vollständig manuell verwendet werden.

Der Scheduler dient ausschließlich zur Automatisierung.

---

# Wozu dient die Job-Queue?

Die Job-Queue sorgt dafür, dass Aufgaben nacheinander abgearbeitet werden.

Dadurch können mehrere Synchronisierungen und Downloads geplant werden, ohne dass sie sich gegenseitig beeinflussen.

---

# Muss ich Plugins installieren?

Nein.

MediaHub funktioniert vollständig ohne Plugins.

Plugins erweitern das Programm lediglich um zusätzliche Funktionen.

---

# Wo finde ich die Logdateien?

Die Logdateien befinden sich im Log-Ordner.

Dieser kann direkt aus MediaHub geöffnet werden.

---

# Wie aktualisiere ich die Dokumentation?

Nach Änderungen genügt:

```text
python build_docs.py
```

Anschließend werden automatisch erzeugt:

- TXT
- HTML
- DOCX
- PDF
- Hilfeindex

---

# Siehe auch

- Hilfe-Center
- Health Check
- Recovery Center