# Installation

Diese Dateien in den MediaHub-Hauptordner kopieren und vorhandene Dateien überschreiben:

- `.github/workflows/build.yml`
- `.github/workflows/release.yml`
- `README.md`
- `publish_release.py`
- `RELEASE_NOTES_PENDING.md`

Danach:

```powershell
git add -A
git commit -m "MediaHub v1.0.5 – Release-Informationen und Node-24-Workflows aktualisiert"
git push origin main
```

Ein Tag-Workflow verwendet die Workflow-Datei aus dem Commit, auf den der Tag zeigt.
Falls v1.0.5 noch nicht erfolgreich veröffentlicht wurde, muss der Tag anschließend
auf den neuen Commit gesetzt und erneut gepusht werden.
