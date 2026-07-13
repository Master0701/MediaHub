# Changelog

## 0.12.6
- Sitzungstoken wird sofort im Arbeitsspeicher verwendet.
- Einzelne 401-Antworten lösen nicht mehr direkt eine erneute Kopplung aus.
- Autorisierung wird zentral bestätigt und die Anfrage einmal wiederholt.

## 0.12.4
- Mobile Kopplung mit Zeitlimit und direkter Token-Prüfung stabilisiert.
- HTTP-Antworten enthalten jetzt Content-Length und schließen die Verbindung sauber.
- Dashboard öffnet sich direkt nach bestätigter Kopplung ohne Seitenneustart.

## v0.12.4

- Kopplungstoken wird nach erfolgreicher Kopplung vor allen geschützten Abfragen übernommen.
- Dashboard öffnet sich erst nach bestätigter Autorisierung.
- Irreführender Platzhalter `000000` wurde durch einen neutralen Hinweis ersetzt.
- Kopplungsfenster bleibt bei fehlender Autorisierung sichtbar und verschwindet nach erfolgreicher Prüfung.

## v0.12.1

- Gerätename bleibt während der Kopplung frei editierbar.
- Wiederholte 401-Antworten setzen das Kopplungsformular nicht mehr zurück.
- Nach erfolgreicher Kopplung wird WebRemote automatisch mit dem gespeicherten Token neu geöffnet.
- Klare Erfolgsmeldung und Eingabeprüfung für den sechsstelligen Code.


## 0.12.0

- QR-Code und sechsstelliger Einmalcode für die Geräte-Kopplung ergänzt.
- Heimnetz-Zugriff kann auf gekoppelte Geräte beschränkt werden.
- Tokens werden nur lokal im Browser gespeichert.
- Gekoppelte Geräte können im MediaHub Plugin-Center einzeln oder vollständig entfernt werden.
- Einmalcode kann jederzeit neu erzeugt werden.
- Gemeinsame Web-Runtime um lokale Authentifizierung erweitert.

## 0.11.0
- Konfigurierbarer Modus: nur dieser Computer oder Heimnetz.
- Port und Gerätename als Plugin-Einstellungen im MediaHub-Plugin-Center.
- Anzeige der lokalen und Heimnetz-Adresse.
- Shared Web Runtime bleibt für Mobile Dashboard wiederverwendbar.


## 0.10.2

- Downloads aus dem Web-Assistenten öffnen kein natives MediaHub-Dialogfenster mehr.
- Nach dem Start wechselt WebRemote automatisch zur Live-Downloadseite.
- Live-Downloadstatus wird im Sekundentakt aktualisiert.
- Repository-README auf den aktuellen WebRemote-Stand gebracht.

## v0.10.1

- Sichtbarer Ladehinweis beim Kanaleinlesen
- Kanalbild und Banner im Web-Assistenten
- Option „Danach neue Videos zur Download-Auswahl öffnen“ wie im Original
- Vollständige Videoauswahl im Browser mit Vorschaubildern, Suche und Downloadstart

# Changelog – MediaHub WebRemote

## v0.10.0
- kompletter Start-/Download-Assistent direkt im Browser
- sechs Schritte: Quelle, Ordner, Benennung, Playlists, Automatisierung, Zusammenfassung
- YouTube-Kanalinfos und Playlists werden über dieselben MediaHub-Dienste geladen
- Kanal, Job und Scheduler-Aufgabe können gespeichert werden
- optional sofort synchronisieren oder synchronisieren und Downloadauswahl öffnen
- Schreiben erfolgt weiterhin ausschließlich über die zentrale Action-Registry im Qt-Hauptthread

# WebRemote v0.10.0

- Zentrale Action-Registrierung in WebRemote und MediaHub-Plugin-API.
- Start-Assistent `setup_wizard.open` dauerhaft freigegeben.
- Aktionsnamen werden nicht mehr in mehreren Whitelists getrennt gepflegt.
- Fehlermeldungen nennen unbekannte Aktionen eindeutig.

# WebRemote v0.8.2

- Assistent-Schaltfläche öffnet jetzt den richtigen Start-/Download-Assistenten.
- Freigegebene Aktion auf `setup_wizard.open` umgestellt.
- Versions- und Katalogdaten konsistent aktualisiert.

# WebRemote v0.8.1

- Fehlende Browser-Funktion `runAction()` ergänzt.
- Schreibaktionen zeigen jetzt Bestätigung und Rückmeldung.
- Kanal-Synchronisierung übergibt den korrekten Kanalindex.

# Changelog

## 0.12.6
- Sitzungstoken wird sofort im Arbeitsspeicher verwendet.
- Einzelne 401-Antworten lösen nicht mehr direkt eine erneute Kopplung aus.
- Autorisierung wird zentral bestätigt und die Anfrage einmal wiederholt.

## 0.8.1
- Kontrollierte Schreibaktionen ergänzt.
- Kanal-Synchronisierung, Downloadsteuerung, Jobs, Scheduler, Assistent und Plugin-Center.
- Bestätigung vor jeder Aktion.

# Changelog

## 0.12.6
- Sitzungstoken wird sofort im Arbeitsspeicher verwendet.
- Einzelne 401-Antworten lösen nicht mehr direkt eine erneute Kopplung aus.
- Autorisierung wird zentral bestätigt und die Anfrage einmal wiederholt.

## 0.6.1

- Zentrale Aktionsleiste direkt im Dashboard ergänzt.
- Schnellzugriffe auf Assistent, Kanäle, Downloads und Plugins.
- Aktuelle Seite kann direkt neu geladen werden.
- Keine neue Schreibberechtigung; alle Aktionen bleiben Navigation oder Aktualisierung.

 – MediaHub WebRemote

## 0.6.0
- Vollständiger lesender Ausbau: Dashboard, Kanäle, Playlists, Bibliothek, Downloads, Jobs, Scheduler, Statistik, Plugins, System und Aktivitäten.
- Keine Steuer- oder Schreibfunktionen.
- Private Pfade und Zugangsdaten werden nicht ausgegeben.

## 0.5.3
- Live-Aktivitäten ergänzt.
