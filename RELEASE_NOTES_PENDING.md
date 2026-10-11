# MediaHub v1.0.24

## Raspberry-Pi-AI-Node: Plugin-Backups und Wiederherstellung

- Neuer Reiter „Backups & Wiederherstellung“ in der Plugin-Verwaltung.
- Anzeige vorhandener Plugin-Backups direkt im MediaHub-Hauptprogramm.
- Backups bleiben auch nach der Deinstallation eines AI-Node-Plugins sichtbar.
- Nicht mehr installierte Plugins werden in der Auswahl mit „(nicht installiert)“ gekennzeichnet.
- Anzeige von Plugin-Version, Erstellungsdatum und Backup-Größe.
- Korrekte Umrechnung der UTC-Backup-Zeitstempel in die lokale Uhrzeit.
- Vereinfachte Backup-Liste mit Version, Datum und Größe.
- Zusätzliche Detailansicht mit Backup-ID und Speicherort auf dem AI-Node.
- Wiederherstellung eines ausgewählten Plugin-Backups mit vorheriger Bestätigung.
- Endgültiges Löschen einzelner Backups mit Sicherheitsabfrage.
- Aktualisierung der Backup-Liste und Beibehaltung der Plugin-Auswahl beim Neuladen.

## AI-Node-Kommunikation

- Neue API-Anbindung zum Abrufen aller Plugin-IDs mit vorhandenen Backups.
- Neue Service-Funktionen zum Auflisten, Wiederherstellen und Löschen von Plugin-Backups.
- Verbesserte Prüfung der vom AI-Node zurückgegebenen Backup-Daten.
- Unterstützung individueller Zeitlimits für API-Anfragen.
- Installationsbestätigung mit einem Zeitlimit von 60 Sekunden.

## AI-Plugin-Installation

- Verbesserte Verarbeitung von Installationsplänen mit dem Status `ready_for_confirmation`.
- Zusätzliche Prüfung auf eine gültige Plugin-ID.
- Nach der Installationsbestätigung wird der tatsächliche Plugin-Status auf dem AI-Node kontrolliert.
- Bei einer Zeitüberschreitung der Bestätigung wird geprüft, ob die Installation trotzdem abgeschlossen wurde.
- Eine Installation gilt erst als bestätigt, wenn das Plugin aktiviert und geladen ist.
- Zusätzliche Fehlermeldungen, wenn ein Plugin nicht erfolgreich bereitgestellt werden konnte.

## Tests und Prüfung

- Backup-Anzeige nach Deinstallation eines AI-Node-Plugins erfolgreich getestet.
- Wiederherstellung des GLiNER-Plugins v0.1.1 aus einem vorhandenen Backup erfolgreich getestet.
- Backup-Erhalt nach der Wiederherstellung bestätigt.
- Backup-Zeitstempel und Größenangaben anhand der AI-Node-Daten überprüft.
- Python-Syntaxprüfung der geänderten MediaHub-Dateien erfolgreich.
- Git-Diff-Prüfung ohne Fehler.

## Hinweise

- Die bestehende Raspberry-Pi-Online-Installation bleibt unverändert.
- Die AI-Node-Backend-Erweiterungen werden separat im Repository MediaHub-AI-Node verwaltet.
- Eine weitergehende Verbesserung der GUI-Reaktionsfähigkeit während längerer Installationsprüfungen bleibt für eine spätere Überarbeitung vorgesehen.