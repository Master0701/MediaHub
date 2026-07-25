# MediaHub KI-Assistent v1.0.0

Der KI-Assistent verbindet Medienerkennung, In-Video-Planung und eine neue Quality Engine.

## Neu in v1.0.0

- Decision Engine mit gewichteten, unabhängigen Beweisen
- Widerspruchserkennung zwischen Dateiname, Online-Treffern und Videoinhalt
- nachvollziehbare Gesamtsicherheit und Vertrauensstufe
- korrigierter Supervisor-Abschlussstatus
- In-Video-Manager mit getrennten Frame-, OCR-, Untertitel-, Audio-, Fingerprint- und Szenenagenten
- gemeinsamer Analyseplan, damit Medienerkennung und Qualitätsprüfung dieselben Daten verwenden
- aktive technische Bildqualitätsbewertung
- aktive technische Audioqualitätsbewertung
- getrennte Bild-, Ton- und Gesamtpunktzahl
- Status: sehr gut, gut, noch akzeptabel, verbesserungswürdig oder neu in besserer Qualität suchen
- persönliche Referenzprofile werden lokal vorbereitet und gespeichert
- Qualitätsentscheidungen führen niemals automatisch zu Löschung oder Austausch

## Nächste Ausbaustufe

Für v1.0.0 folgen die stabilen Plugin-Schnittstellen zum Metadata Editor und Universal Renamer, die Wissensbeziehungen sowie die abschließenden Release- und Lizenzprüfungen.


Optional können Umgebungsvariablen gesetzt werden:

- `MEDIAHUB_TMDB_API_KEY` oder `MEDIAHUB_TMDB_BEARER_TOKEN`
- `MEDIAHUB_TVDB_API_KEY`
- `MEDIAHUB_TVDB_SUBSCRIBER_PIN` nur bei einem entsprechenden TheTVDB-Schlüssel

Wikipedia ist standardmäßig aktiviert und benötigt keinen Schlüssel.

## v1.0.0 – stabile KI-Grundarchitektur

- Erklärbare Entscheidung mit Begründung, Einschränkungen und Widersprüchen
- Lokale Fingerprint-Referenzdatenbank; Einträge nur nach Benutzerbestätigung
- Stabile Integrations-API (Schema 1) für Metadata Editor und Universal Renamer
- Keine automatische Änderung ohne Vorschau und Bestätigung
- Supervisor, Decision Engine und ausgeführte Agenten verwenden denselben finalen Zustand
