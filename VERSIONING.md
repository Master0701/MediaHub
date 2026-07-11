# MediaHub-Versionsverwaltung

Die einzige Versionsnummer, die bei einem neuen Release manuell geändert wird, steht in:

```python
src/mediahub/app_info.py
APP_VERSION = "1.0.3"
```

Vor einem Build erzeugt `mediahub_version.py` automatisch:

- `version_info.txt` für die Windows-Dateiversion der EXE
- `installer/version_generated.iss` für Inno Setup
- versionierte Namen der Portable-, Setup- und Handbuch-Pakete

## Neuer Release

1. `APP_VERSION` in `src/mediahub/app_info.py` ändern.
2. `CHANGELOG.md` ergänzen.
3. Lokal prüfen: `python mediahub_version.py`
4. Commit und Tag mit derselben Version erstellen.
5. Den Tag zu GitHub übertragen; der Release-Workflow baut die Downloads automatisch.

Der Tag muss zur Version passen, zum Beispiel `APP_VERSION = "1.0.3"` und Git-Tag `v1.0.3`.
