# MediaHub Release-Assistent v2

## Dateien ersetzen

- `build_release.py`
- `publish_release.py`
- `src/mediahub/gui/release_assistant_dialog.py`

## Datei in den MediaHub-Hauptordner legen

- `RELEASE_NOTES_PENDING.md`

## Neuer Ablauf

1. Release-Assistent liest `RELEASE_NOTES_PENDING.md`.
2. Die Notizen werden im Dialog angezeigt.
3. Ohne Notizen startet kein komplettes Release.
4. Die Commit-Nachricht wird aus `## Commit-Nachricht` übernommen.
5. `CHANGELOG.md` erhält die aktuellen Notizen.
6. `build_release.py` kopiert sie nach `release/RELEASE_NOTES.md`.
7. `publish_release.py` verwendet die Commit-Nachricht automatisch.
8. Erst wenn der gesamte Prozess erfolgreich mit Exit-Code 0 endet, löscht der Dialog die temporäre Datei.
9. Bei einem Fehler bleibt die Datei erhalten.

## Nicht geändert

- `release_gate.py`
- `build.py`
- `src/mediahub/app_info.py`

## Kompakte Oberfläche

Die zusätzliche Release-Notiz-Anzeige im Hauptfenster wurde entfernt. Die Datei wird weiterhin intern geprüft und verarbeitet.
