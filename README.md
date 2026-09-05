# MediaHub v1.0.21

MediaHub ist ein lokales PySide6-Programm zum Verwalten von YouTube-Kanälen, Playlists, Video-Downloads, Plex-Importen und separat installierbaren Erweiterungen.

## Neu und verbessert in v1.0.21

# MediaHub v1.0.21

## Node-/KI-Infrastruktur

- Gemeinsame Node-Worker-Anbindung für MediaHub-Plugins vorbereitet und erweitert.
- Fähigkeiten wie `speech_to_text` können über geeignete installierte und erreichbare Worker-Nodes ausgeführt werden.
- Windows Compute Node und Raspberry-Pi-/AI-Node bleiben getrennte Nodes, können aber über dieselbe capability-basierte Worker-Schnittstelle angesprochen werden.
- MediaHub überträgt große Job-Eingabedateien gestreamt an den ausgewählten Node statt sie vollständig in den Arbeitsspeicher zu laden.
- Job-Eingaben werden node-seitig in verwalteten Job-Input-Verzeichnissen gespeichert.
- Job-Ausführung kann bis zum terminalen Zustand `completed`, `failed` oder `cancelled` verfolgt werden.
- Lange Speech-/Analysejobs werden per Status-Polling verfolgt; ein lokaler Client-Timeout beendet den Remote-Job nicht automatisch.

## MediaHub-KI-/Plugin-Integration

- Der KI-Assistent kann die MediaHub-Laufzeitbasis und die zentrale Node-Worker-Infrastruktur verwenden.
- Provider- und Plugin-Laufzeitdaten bleiben von den Plugin-Codepfaden getrennt.
- Gespeicherte Provider-Einstellungen und Zugangsdaten können dadurch auch beim Arbeiten mit einer Entwicklungs-Plugin-Kopie aus dem echten MediaHub-Laufzeitverzeichnis verwendet werden.
- Grundlage für die reale In-Video-/Speech-Erkennung anonymisierter Medien wurde im Hauptprogramm bereitgestellt.

## Stabilität

- Node-Verfügbarkeit, Plugin-/Worker-Capabilities und Ausführungsstatus werden vor der Aufgabenvergabe berücksichtigt.
- Nicht verfügbare Worker dürfen nicht stillschweigend als funktionsfähig behandelt werden.
- Bestehender Raspberry-Pi-Online-Installer bleibt unverändert.
- Windows Compute Node behält seinen getrennten Installations- und Release-Weg.

## Release

- MediaHub-Version: 1.0.20 -> 1.0.21
- Vor Veröffentlichung Build, Installer, Drittanbieter-Lizenzen und Release-Paket vollständig prüfen.
- Release-Tag muss auf den aktuellen vorgesehenen Release-Commit zeigen.
- GitHub-Release-Titel und Release-Text müssen aus dieser aktuellen Datei erzeugt werden.

Die vollständige Versionshistorie steht in [`CHANGELOG.md`](CHANGELOG.md).

## Start aus dem Quellcode

```powershell
python -m pip install -r requirements.txt
python main.py
```
