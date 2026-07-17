# Plugin-System

Das Plugin-System ist vorbereitet.

Ein Plugin kann später aus folgenden Dateien bestehen:

- plugin.json
- main.py
- help.md

## Fremdsoftware in Plugins

Plugins, die fremde Bibliotheken, Modelle, Bilder, Sprachdaten oder zusätzliche Programme verwenden bzw. installieren, müssen die jeweiligen Urheber- und Lizenzhinweise im Plugin-Paket mitführen. Bevorzugt wird eine Datei `THIRD_PARTY_NOTICES.md` im Hauptordner des Plugins. Die Rechte bleiben vollständig bei den jeweiligen Rechteinhabern.

Die Manifest-Felder `required_tools` und `optional_tools` beschreiben nur die technische Abhängigkeit. Sie ersetzen keine Lizenzdatei und keine vorgeschriebenen Copyright-Hinweise.
