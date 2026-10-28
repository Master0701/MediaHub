# MediaHub v1.0.25

## Windows Compute Node – sichere Plugin-Installation

- Die Installation von `.mhaiplugin`-Paketen über den MediaHub-Plugin-Store wurde auf einen zweistufigen Ablauf umgestellt: zunächst Installationsplan erstellen, anschließend ausdrücklich bestätigen.
- MediaHub ruft dafür die Plan-Schnittstelle des Windows Compute Node auf und führt die eigentliche Installation erst nach Zustimmung im Plugin-Store aus.
- Vor der Bestätigung zeigt MediaHub Pluginname, Version, Ziel-Node, vorgesehene Aktion sowie die im Plan genannten Python-Pakete und Node-Plugin-Abhängigkeiten an.
- Python-Pakete werden, soweit erforderlich, im isolierten Runtime-Ordner des Node-Plugins installiert. Benötigte zusätzliche Node-Plugins werden nicht stillschweigend installiert.
- Die SHA-256-Prüfsumme des vom Node zurückgegebenen Installationsplans wird mit dem geprüften Plugin-Paket abgeglichen. Ungültige oder nicht passende Planinformationen führen zum Abbruch.
- Plan-ID und SHA-256-Prüfsumme werden vor der Bestätigung geprüft. Die Kommunikation mit dem Node berücksichtigt weiterhin die konfigurierte Token-Authentifizierung.
- Nicht bestätigte beziehungsweise nach der Bestätigung nicht mehr benötigte Installationspläne werden nach Möglichkeit über die Node-Schnittstelle verworfen.
- Fehler bei der Kommunikation oder bei ungültigen Installationsantworten werden als Node-Verbindungs- beziehungsweise Installationsfehler behandelt.

## Kompatibilität

- Die aktualisierte Installationsfunktion setzt einen Windows Compute Node mit Unterstützung für die Endpunkte `/plugins/plan` und `/plugins/plan/{plan_id}/confirm` voraus.
- Der Windows Compute Node v0.1.4 und die vorbereiteten Node-Plugin-Versionen werden getrennt vom MediaHub-Hauptprogramm bereitgestellt; sie sind nicht Bestandteil dieses Hauptprogramm-Releases.
- Die bestehende Raspberry-Pi-Installation und deren Online-Installer werden durch diese Änderung nicht ersetzt.

## Release

- Zielversion: MediaHub v1.0.25.
- Die Versionsanhebung, die Aktualisierung von README und Changelog sowie Build und Veröffentlichung erfolgen ausschließlich über den vorhandenen MediaHub-Release-Assistenten.
- Release-Tag, GitHub-Release-Titel und GitHub-Release-Beschreibung müssen die Version v1.0.25 und diese aktuellen Änderungen wiedergeben.

## Commit-Nachricht

MediaHub v1.0.25 – Windows Compute Node Installationsplan und bestätigte Plugin-Installation
