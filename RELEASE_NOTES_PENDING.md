# Änderungen

## Zentrale Plugin-Werkzeugverwaltung

- Plugin-Werkzeuge werden aus einfachen IDs und strukturierten Objekten in `plugin.json` erkannt.
- Pflicht- und optionale Werkzeuge werden bei der Plugin-Installation berücksichtigt.
- Bereits vorhandene Werkzeuge werden erkannt und übersprungen.
- Fehlende Werkzeuge werden automatisch eingerichtet.

## Portable Werkzeuge ohne Administratorrechte

- MediaInfo wird portabel unter `MediaHub\tools` eingerichtet.
- MKVToolNix wird als offizielles `.7z`-Archiv geladen und portabel entpackt.
- Tesseract OCR wird als portables Paket aus dem Repository `MediaHub_Tools` installiert.
- FFprobe wird korrekt als von Plugins verwendetes Werkzeug registriert.

## Tool-Assistent und globale Einstellungen

- Der Tool-Assistent öffnet deutlich schneller.
- „Alles prüfen“ zeigt anschließend die tatsächlichen Prüf- und Versionsinformationen an.
- Der Tool-Status in den globalen Einstellungen behält die bestehende Ansicht und ordnet Werkzeuge in Viererblöcken nebeneinander an.
- Die Plugin-Installation zeigt den Fortschritt der Werkzeugprüfung und Einrichtung in einem eigenen Fenster.

## Kompatibilität

- Grundlage für den MediaHub KI-Assistenten v0.4.1 und zukünftige Plugins mit externen Werkzeugen.

## Commit-Nachricht

Zentrale Plugin-Werkzeugverwaltung und portable Tools fertigstellen
