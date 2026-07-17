# Hinweise zu Fremdsoftware und Lizenzen

MediaHub verwendet und verwaltet externe Programme, Bibliotheken und Plugins. Diese Bestandteile bleiben Eigentum ihrer jeweiligen Urheber und Rechteinhaber. Ihre Nutzung und Weitergabe richtet sich ausschließlich nach den jeweiligen Original-Lizenzen.

MediaHub beansprucht keine Rechte an diesen Drittkomponenten. Die Aufnahme in ein MediaHub-Installationspaket, der automatische Download oder die Nutzung durch ein Plugin ändert die ursprünglichen Lizenz- und Urheberrechte nicht.

## Vom Hauptprogramm verwendete Werkzeuge

| Komponente | Projekt / Rechteinhaber | Lizenzhinweis |
|---|---|---|
| yt-dlp | yt-dlp contributors | Quellprojekt: The Unlicense. Vorgefertigte ausführbare Dateien können weitere Drittkomponenten und abweichende Lizenzpflichten enthalten; die mitgelieferten Lizenzdateien des jeweiligen Downloads sind maßgeblich. |
| FFmpeg / ffprobe | FFmpeg project contributors | Je nach Build LGPL oder GPL sowie zusätzliche Komponentenlizenzen. Maßgeblich sind die Lizenzinformationen des tatsächlich verwendeten Builds. |
| Deno | Deno Land Inc. und Mitwirkende | MIT License. |
| PySide6 / Qt for Python | The Qt Company und Mitwirkende | Lizenzbedingungen der verwendeten PySide6-/Qt-Ausgabe sind maßgeblich. |
| requests | Kenneth Reitz und Mitwirkende | Apache License 2.0. |

## Von Plugins verwendbare Zusatzwerkzeuge

| Komponente | Projekt / Rechteinhaber | Lizenzhinweis |
|---|---|---|
| MediaInfo | MediaArea.net SARL und Mitwirkende | BSD 2-Clause License. |
| Tesseract OCR | Google LLC, Tesseract-Mitwirkende und weitere Rechteinhaber | Apache License 2.0; Abhängigkeiten und Sprachdaten können eigene Lizenzen besitzen. |
| MKVToolNix | Moritz Bunkus und Mitwirkende | Die Lizenzbedingungen der konkret installierten MKVToolNix-Ausgabe sind maßgeblich. |

## Plugins

Jedes MediaHub-Plugin ist eine eigenständige, optionale Erweiterung. Für Code, Bilder, Bibliotheken, Modelle, Sprachdaten und Zusatzwerkzeuge eines Plugins gelten die Angaben des jeweiligen Plugin-Herausgebers.

Jedes Plugin-Paket soll eine eigene Datei `THIRD_PARTY_NOTICES.md`, `NOTICE`, `LICENSE` oder eine gleichwertige Lizenzdokumentation mitführen, sobald es fremde Bestandteile enthält oder zusätzliche Werkzeuge installiert. MediaHub bewahrt solche Dateien beim Installieren des Plugins im jeweiligen Plugin-Ordner auf.

## Maßgebliche Originalunterlagen

Diese Übersicht dient der Zuordnung und ersetzt keine Original-Lizenz. Bei Abweichungen gelten immer die Lizenztexte, Copyright-Hinweise und Drittanbieterinformationen, die mit dem jeweiligen Programm, Build, Python-Paket, Plugin oder Zusatzinhalt ausgeliefert werden.

Projektseiten:

- yt-dlp: https://github.com/yt-dlp/yt-dlp
- FFmpeg: https://ffmpeg.org/
- Deno: https://github.com/denoland/deno
- PySide6 / Qt for Python: https://doc.qt.io/qtforpython-6/
- requests: https://github.com/psf/requests
- MediaInfo: https://github.com/MediaArea/MediaInfo
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- MKVToolNix: https://mkvtoolnix.download/
