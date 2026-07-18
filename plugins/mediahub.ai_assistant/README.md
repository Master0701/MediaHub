# MediaHub KI-Assistent 0.1.0

Erste testbare Grundversion von Plugin 4.

## Enthalten

- automatische Anlage von `config/knowledge.sqlite3`
- WAL-Modus und gezielte Indizes für schnelle SQLite-Abfragen
- versioniertes Datenbankschema
- ausschließlich lesender Zugriff auf `config/mediahub.sqlite3`
- eigenes Desktop-Fenster mit Systemstatus
- vorbereitete Tabellen für Medien, Beziehungen, Editionen und Erkennungs-Cache
- keine feste Abhängigkeit von einem KI-Anbieter

## Noch nicht enthalten

Die eigentliche Film-/Serien- und Editionserkennung wird schrittweise auf diesem Grundsystem aufgebaut.
