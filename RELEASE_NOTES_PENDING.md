# MediaHub – AI-Node- und AI-Plugin-Integration

## Änderungen

- AI-Node-Verbindungsstatus überarbeitet und zuverlässiger aktualisiert.
- Erkennung und Anzeige der AI-Node-Version verbessert.
- AI-Node-Heartbeat und Anzeige der letzten Aktivität korrigiert.
- Unterstützung der lokalen AI-Node-Statusseite im Heimnetz ergänzt.
- AI-Plugin-Katalog vollständig in die vorhandene AI-Plugin-Verwaltung integriert.
- Installierte AI-Node-Plugins und verfügbare Katalog-Plugins werden gemeinsam dargestellt.
- Neuer Plugin-Status und Filter „Nicht installiert“ ergänzt.
- Katalogeinträge werden mit bereits installierten AI-Node-Plugins zusammengeführt, sodass keine doppelten Einträge entstehen.
- „AI-Katalog aktualisieren“ aktualisiert die sichtbaren verfügbaren und installierten AI-Plugins.
- Nicht installierte Raspberry-Pi-AI-Plugins können direkt über „Aus Katalog installieren“ installiert werden.
- Katalogpakete werden vor der Installation über SHA-256 verifiziert.
- Die Installation verwendet weiterhin den sicheren AI-Node-Installationsplan mit Benutzerbestätigung.
- Der bestehende manuelle Installer für `.mhaiplugin`-/ZIP-Pakete bleibt erhalten.
- Nach erfolgreicher Installation wird die AI-Plugin-Liste automatisch neu geladen.
- AI-Node- und Compute-Node-Service wurden an die aktualisierte Status- und Verbindungsbehandlung angepasst.

## Getestet

- AI-Node-Verbindung erfolgreich.
- AI-Plugin-Katalog wird in MediaHub angezeigt.
- Nicht installierte Plugins werden korrekt dargestellt und gefiltert.
- Installation eines AI-Plugins direkt aus dem Katalog erfolgreich getestet.
- Installiertes Plugin wird anschließend korrekt in MediaHub erkannt.
- Installiertes Plugin wird auf der AI-Node-Statusseite angezeigt.
- Erneute Katalogaktualisierung erzeugt keinen doppelten Plugin-Eintrag.
