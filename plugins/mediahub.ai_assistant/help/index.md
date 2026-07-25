# MediaHub KI-Assistent

Version 0.1.0 legt die technische Grundlage an. Beim Start wird die Wissensdatenbank
`config/knowledge.sqlite3` neben der bestehenden `config/mediahub.sqlite3` erzeugt.

Die MediaHub-Datenbank wird nur schreibgeschützt geöffnet.


## Erklärbare Entscheidung

Der Bereich „KI-Entscheidung“ nennt nicht nur einen Prozentwert. Er zeigt bestätigende Gründe, noch nicht eindeutige Hinweise, erkannte Widersprüche und eine verständliche Schlussfolgerung.

## Fingerprint-Referenzen

Ein erzeugter Fingerprint ist zunächst nur ein Vergleichsschlüssel. Erst wenn der Benutzer die erkannte Identität bestätigt und die Referenz speichert, kann derselbe Fingerprint künftig als starker Identitätsbeweis dienen.

## Plugin-Übergabe

Metadata Editor und Universal Renamer erhalten ein versioniertes, schreibgeschütztes Übergabepaket. Änderungen bleiben Vorschläge und werden niemals ohne Vorschau und Bestätigung ausgeführt.
