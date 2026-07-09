# MediaHub Installer Update 05

Fix für den Deinstallations-Test.

## Behoben

- `downloads`, `backups`, `database`, `config`, `logs`, `plugins`, `tools` und `archive`
  werden jetzt mit `uninsneveruninstall` geschützt.
  Dadurch löscht Inno Setup diese Ordner nicht mehr automatisch.

- `MediaHub.exe` wird beim Deinstallieren gezielt entfernt.

- Falls MediaHub beim Deinstallieren noch läuft, wird `MediaHub.exe` vorher beendet.

## Wichtig

Persönliche Daten werden weiterhin nur über die Abfragen im Uninstaller gelöscht.

## Datei ersetzen

```text
installer\installer.iss
```

Danach:

```bat
python build.py
```

## Test

1. In Testordner installieren.
2. Testdatei in `downloads` anlegen.
3. Deinstallieren und bei Downloads **Nein / behalten** wählen.
4. Prüfen:
   - `MediaHub.exe` muss weg sein.
   - `downloads` muss bleiben.
