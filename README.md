# MediaHub v1.0.22

MediaHub ist ein lokales PySide6-Programm zum Verwalten von YouTube-Kanälen, Playlists, Video-Downloads, Plex-Importen und separat installierbaren Erweiterungen.

## Neu und verbessert in v1.0.22

# MediaHub v1.0.22

## Build- und Release-System

- PyInstaller-Build für GitHub Actions korrigiert.
- `MediaHub.spec` enthält keine rechnerabhängigen absoluten Entwicklungspfade mehr.
- Der Programmeinstieg `main.py` wird jetzt portabel relativ zum Speicherort der Spec-Datei aufgelöst.
- Der `assets`-Ordner wird ebenfalls portabel relativ zum Projektverzeichnis eingebunden.
- `version_info.txt` wird ohne lokalen Entwicklerpfad in den PyInstaller-Build übernommen.
- Das MediaHub-Programmsymbol wird portabel aus `assets/icons/mediahub.ico` geladen.
- Dadurch kann derselbe `MediaHub.spec` sowohl auf dem Entwicklungsrechner als auch auf GitHub-Actions-Runnern verwendet werden.

## Release

- MediaHub-Version: 1.0.21 -> 1.0.22
- Dieser Release behebt den fehlgeschlagenen GitHub-Actions-/PyInstaller-Build von v1.0.21.
- Der bestehende historische Release-Tag `v1.0.21` bleibt unverändert.
- Release-Tag `v1.0.22` muss auf den aktuellen vorgesehenen Release-Commit zeigen.
- GitHub-Release-Titel und Release-Text müssen aus den aktuellen Release-Notizen erzeugt werden.

Die vollständige Versionshistorie steht in [`CHANGELOG.md`](CHANGELOG.md).

## Start aus dem Quellcode

```powershell
python -m pip install -r requirements.txt
python main.py
```
