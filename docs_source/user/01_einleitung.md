# Willkommen bei MediaHub

MediaHub ist ein Werkzeug zur Verwaltung von YouTube-Kanälen, Playlists, bekannten Videos, Downloads, Zeitplänen, Backups und Hilfswerkzeugen.

Dieses Handbuch erklärt die Bedienung Schritt für Schritt. Es ist so geschrieben, dass du MediaHub auch ohne technisches Vorwissen benutzen kannst.

## Was MediaHub macht

Mit MediaHub kannst du:

- Kanäle anlegen und verwalten
- Playlists eines Kanals auslesen
- neue Videos erkennen
- Downloads vorbereiten und starten
- externe Tools wie yt-dlp und FFmpeg prüfen
- automatische Aufgaben planen
- Backups und Wiederherstellungen verwenden
- Logs und Fehler leichter finden
- die integrierte Hilfe nutzen

## Grundidee

MediaHub soll nicht nur einzelne Downloads starten. Das Programm soll dir helfen, deine Kanäle dauerhaft sauber zu verwalten.

Ein typischer Ablauf sieht so aus:

1. Kanal hinzufügen.
2. Playlists und Videos laden.
3. Neue Videos auswählen.
4. Download starten.
5. Ergebnis in Bibliothek, Log und Download-Warteschlange prüfen.
6. Optional automatische Aufgaben über den Scheduler anlegen.

## Wichtige Begriffe

**Kanal**  
Ein gespeicherter YouTube-Kanal mit Name, URL und Einstellungen.

**Playlist**  
Eine Sammlung von Videos eines Kanals.

**Bibliothek**  
Die Datenbank-Ansicht mit bekannten Videos und Downloadstatus.

**Download-Warteschlange**  
Der Bereich, in dem laufende und geplante Downloads angezeigt werden.

**Scheduler**  
Der Bereich für wiederkehrende Aufgaben, zum Beispiel regelmäßige Synchronisierung.

**Recovery Center**  
Der Bereich für Backups, Selbsttests und Wiederherstellung.

## Hinweis zu Screenshots

Die Bilder in diesem Handbuch werden automatisch aus dem Ordner `docs_source/user/images` eingebunden. Wenn ein Screenshot fehlt, zeigt `python build_docs.py` am Ende einen Screenshot-Bericht an.
