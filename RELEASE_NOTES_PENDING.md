# MediaHub v1.0.11 – Native Plugin-Oberflächen

## Neu

- Native Plugin-GUIs werden direkt im MediaHub-Hauptfenster eingebettet.
- Der Metadata Editor besitzt nun eine echte In-Program-Oberfläche mit Kategorien, Medienliste, Metadatenformular, Live-Änderungsanzeige, Entwurfsspeicherung, NFO-Speicherung und Poster-Austausch.

## Verhalten

- Der vorhandene Navigationspunkt **Plugins** und seine Verwaltungs-GUI bleiben unverändert.
- Der zweite Bereich **Plugin-Oberflächen** erscheint weiterhin nur bei mindestens einem aktivierten GUI-Plugin.
- WebRemote und Mobile Dashboard bleiben Browser-Oberflächen.
- Hintergrund-Plugins erscheinen nicht im GUI-Bereich.

## Technik

- Native Plugins liefern ihr Qt-Widget über `create_widget(parent=...)`.
- Der Plugin-Host unterscheidet `native`, `web` und zukünftig `dialog`.
- Alle geänderten Python-, JSON- und Markdown-Dateien sind UTF-8-kodiert.
