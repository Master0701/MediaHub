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

## Plugins und Zusatzwerkzeuge

Jedes Plugin muss eigene Lizenz- und Drittanbieterhinweise in seinem Paket mitführen. Plugin-spezifische Originaltexte bleiben im jeweiligen Plugin-Ordner erhalten. Der Tool-Manager zeigt zusätzlich die hinterlegte Lizenz und Projekt-Homepage an.

## Hinweis zu Binärpaketen

MediaHub lädt einige Werkzeuge erst bei Installation oder Nutzung von den offiziellen beziehungsweise konfigurierten Projektquellen herunter. Die dabei mitgelieferten Originalhinweise und Lizenzdateien haben Vorrang vor dieser Übersicht.
