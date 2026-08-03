# Drittanbieter-Lizenzen

Diese Datei ordnet die von MediaHub verwendeten Bibliotheken und externen Werkzeuge den im Ordner `licenses/` enthaltenen Lizenztexten zu. Maßgeblich bleiben stets die Lizenz- und Copyright-Dateien der konkret installierten oder heruntergeladenen Ausgabe.

| Komponente | Lizenz | Lokaler Lizenztext |
|---|---|---|
| yt-dlp | Unlicense; Binärpakete können weitere Hinweise enthalten | `licenses/Unlicense.txt` |
| FFmpeg / ffprobe / ffplay | Je nach verwendetem Build GPL oder LGPL sowie Komponentenlizenzen | `licenses/GPL-2.0.txt`, `licenses/LGPL-3.0.txt` |
| Deno | MIT | `licenses/MIT.txt` |
| PySide6 / Qt for Python | LGPL/GPL beziehungsweise kommerzielle Qt-Lizenz, abhängig von der verwendeten Distribution | `licenses/LGPL-3.0.txt`, `licenses/GPL-2.0.txt` |
| requests | Apache-2.0 | `licenses/Apache-2.0.txt` |
| MediaInfo | BSD-2-Clause | `licenses/BSD-2-Clause.txt` |
| Tesseract OCR | Apache-2.0 | `licenses/Apache-2.0.txt` |
| MKVToolNix | GPL-2.0-or-later | `licenses/GPL-2.0.txt` |
| ReNamer Portable | Lite: CC BY-NC-ND 3.0, nur nicht-kommerziell; für kommerzielle Nutzung ist eine Pro-Lizenz erforderlich | `licenses/CC-BY-NC-ND-3.0.txt` |

## Plugins und Zusatzwerkzeuge

Jedes Plugin muss eigene Lizenz- und Drittanbieterhinweise in seinem Paket mitführen. Plugin-spezifische Originaltexte bleiben im jeweiligen Plugin-Ordner erhalten. Der Tool-Manager zeigt zusätzlich die hinterlegte Lizenz und Projekt-Homepage an.

## Hinweis zu Binärpaketen

MediaHub lädt einige Werkzeuge erst bei Installation oder Nutzung von den offiziellen beziehungsweise konfigurierten Projektquellen herunter. Die dabei mitgelieferten Originalhinweise und Lizenzdateien haben Vorrang vor dieser Übersicht.

## ReNamer Portable

ReNamer wird nicht im MediaHub-Repository gebündelt. Das optionale Windows-
Werkzeug wird nach ausdrücklicher Bestätigung der nicht-kommerziellen Lite-
Nutzung über den MediaHub-Tool-Manager von der offiziellen Herstellerquelle
heruntergeladen und portabel unter `tools/renamer/` eingerichtet.

- Hersteller / Rechteinhaber: Furious Technologies Limited / den4b
- Produktseite: https://www.den4b.com/products/renamer
- Portable Downloadseite: https://www.den4b.com/download/renamer/portable
- Lizenzseite: https://www.den4b.com/license
- Lite: ausschließlich nicht-kommerzielle Nutzung
- Kommerziell: Pro-Lizenz erforderlich
- Im Repository gebündelt: nein
