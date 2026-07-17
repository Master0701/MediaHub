# Lizenzen und Fremdsoftware

MediaHub verwendet externe Programme, Python-Bibliotheken und optionale Plugin-Werkzeuge.

Die Urheberrechte, Markenzeichen und Lizenzbedingungen dieser Bestandteile bleiben bei den jeweiligen Rechteinhabern. MediaHub erhebt daran keine eigenen Rechte.

## Zentrale Lizenzhinweise

Die vollständige Übersicht befindet sich im MediaHub-Hauptordner:

`THIRD_PARTY_NOTICES.txt`

Die gleichlautende Datei `THIRD_PARTY_NOTICES.md` dient zusätzlich der Darstellung auf GitHub und in Entwicklerwerkzeugen.

## Im Hauptprogramm verwendete Werkzeuge

Zu den von MediaHub verwendeten oder automatisch bereitgestellten Werkzeugen gehören insbesondere:

- yt-dlp
- FFmpeg und FFprobe
- Deno

Welche Lizenzbedingungen konkret gelten, hängt teilweise vom verwendeten Build und dessen enthaltenen Komponenten ab. Die verbindlichen Hinweise stehen in `THIRD_PARTY_NOTICES.txt` sowie in den mitgelieferten Original-Lizenzdateien.

## Werkzeuge für Plugins

Plugins können zusätzliche Werkzeuge anfordern, zum Beispiel:

- MediaInfo
- Tesseract OCR
- MKVToolNix

Jedes Plugin muss seine eigenen Fremdsoftware- und Lizenzangaben in seinen Metadaten und seinem Paket mitführen. Gemeinsam genutzte Werkzeuge werden zentral durch MediaHub verwaltet.

## Anzeige im Programm

Die vollständige Textdatei erreichst du über:

**Hilfe → Lizenzen und Fremdsoftware**

## Wichtig

Diese Übersicht ersetzt nicht die Original-Lizenztexte. Bei Abweichungen gelten immer die mit dem jeweiligen Bestandteil gelieferten Originalbedingungen.
