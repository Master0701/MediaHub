MediaHub Release-Notizen-Fix

Enthaltene Dateien in den MediaHub-Hauptordner kopieren und überschreiben:
- build_release.py
- publish_release.py
- .github/workflows/release.yml

Behebung:
- RELEASE_NOTES_PENDING.md wird trotz .gitignore in den Release-Commit aufgenommen.
- Nach dem Tag-Push wird die temporäre Datei auf dem Hauptbranch wieder entfernt.
- Ein Release ohne Release-Notizen wird frühzeitig abgebrochen.
- Der doppelte GitHub-Schritt zum nachträglichen Aktualisieren der Beschreibung wurde entfernt.
