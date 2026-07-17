# Ausstehende Release-Notizen

## MediaHub v1.0.14

### Neu

- Zentrale Fremdsoftware- und Lizenzübersicht für MediaHub, Plugins und zusätzliche Werkzeuge ergänzt.
- Neues Kapitel **Lizenzen und Fremdsoftware** in das integrierte Hilfe-Center aufgenommen.
- Plugin-Manifeste unterstützen jetzt `required_tools` und `optional_tools`.
- Der zentrale ToolService erfasst, welche installierten Plugins ein Werkzeug zwingend oder optional verwenden.

### Verbessert

- Der Menüpunkt **Hilfe → Lizenzen und Fremdsoftware** öffnet nun eine normale TXT-Datei statt einer Markdown-Datei und wird dadurch nicht mehr automatisch in VS Code geöffnet.
- Plugin Center und ToolService wurden verbunden, sodass Werkzeugabhängigkeiten beim Laden, Installieren und Entfernen von Plugins automatisch neu registriert werden.
- Installer, Portable-Paket und Release-Paket übernehmen die Fremdsoftware-Hinweise.
- README, Über-Dialog und Entwicklerdokumentation wurden um klare Lizenzhinweise erweitert.
- Release-Dateien werden weiterhin aus der zentralen MediaHub-Version erzeugt.

### Technischer Hinweis

- Die automatische Installation fehlender Plugin-Werkzeuge wird in einem folgenden Entwicklungsschritt ergänzt. Die Erkennung und zentrale Zuordnung sind bereits vorbereitet.

## Commit-Nachricht

Plugin-Toolverwaltung und Lizenzhinweise ergänzen
