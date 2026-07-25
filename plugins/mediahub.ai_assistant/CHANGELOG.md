# Changelog

## 1.0.0

- Erklärbare KI-Entscheidung mit Gründen, Einschränkungen und Widerspruchserklärung.
- Lokale SQLite-Fingerprint-Referenzdatenbank ergänzt.
- Bestätigte Fingerprints können später eindeutige Medienidentitäten liefern.
- Stabile Integrations-API für Metadata Editor und Universal Renamer ergänzt.
- Sicherheitsvertrag festgeschrieben: Vorschau und Bestätigung vor jeder Änderung.
- Finale Supervisor-/Decision-Engine-Zustände vereinheitlicht.

## 0.9.5

- Neue Decision Engine führt Dateiname, Online-Treffer, OCR, Untertitel, Fingerprint und technische Hinweise zusammen.
- Jede Quelle erhält getrennte Sicherheit, Gewichtung und Begründung.
- Unabhängige Bestätigungen werden gezählt und zu einer nachvollziehbaren Gesamtsicherheit kombiniert.
- Titelwidersprüche zwischen Dateiname und Online-/Inhaltsbeweisen werden ausdrücklich gemeldet.
- Klare Entscheidungsstufen ergänzt: bestätigt, wahrscheinlich, Prüfung empfohlen, unzureichend oder Widerspruch.
- Supervisor übernimmt jetzt den tatsächlichen Abschlusszustand der In-Video-Agenten statt sie nach erfolgreicher Analyse weiter als ausstehend anzuzeigen.
- Automatische Änderungen bleiben auch bei bestätigter Identität gesperrt; Vorschau und Benutzerbestätigung bleiben Pflicht.

## 0.9.0

- Begrenzte echte In-Video-Analyse statt bloßer Ausführungsplanung.
- FrameAgent liest reale Helligkeits-, Kontrast- und Sättigungswerte aus Stichproben.
- SubtitleAgent extrahiert Text, Schlüsselbegriffe und mögliche Eigennamen aus der ersten Untertitelspur.
- AudioAgent misst Lautheit, Dynamik und mögliches Clipping in einer begrenzten Audiostichprobe.
- OCRAgent analysiert ausgewählte Frames mit dem zentral installierten Tesseract.
- FingerprintAgent erzeugt einen reproduzierbaren Fingerprint aus normalisierten Videoframes.
- SceneAgent erkennt Szenenwechsel in einem begrenzten Analysefenster.
- Quality Engine v2 kombiniert technische Daten mit gemessenen Bild- und Audiowerten.
- Analyseausgabe zeigt Status und Zahl der tatsächlich ausgeführten In-Video-Agenten.
- Tiefenanalyse bleibt ressourcenschonend begrenzt und verändert keine Mediendateien.

## 0.8.0

- In-Video-Agent von einem Platzhalter zu einer ausführbaren Orchestrierungsbasis erweitert.
- Frame-, OCR-, Untertitel-, Audio-, Fingerprint-, Szenen- und Quality-Agent als getrennte Stufen definiert.
- Technische Bildqualitätsbewertung ergänzt.
- Technische Audioqualitätsbewertung einschließlich Codec, Bitrate, Kanälen und Abtastrate ergänzt.
- Getrennte Bild-, Ton- und Gesamtbewertung mit nachvollziehbaren Gründen eingeführt.
- Qualitätsstatus für Bibliotheksmarkierungen vorbereitet.
- Persönliche Referenzprofile für akzeptable Mindestqualität ergänzt.
- Qualitätsbewertung führt nie automatisch Änderungen an Medien aus.

## 0.7.0

- Echter ProviderManager mit TMDb, TheTVDB und Wikipedia.
- Einheitliches Online-Trefferformat eingeführt.
- Gewichtetes Mehrquellen-Ranking auf Schema-Version 2 erweitert.
- Staffel, Folge und Laufzeit in die Bewertung aufgenommen.
- Wikipedia als sofort nutzbare schlüssellose Testquelle aktiviert.
- Internet-Berechtigung für Online-Provider ergänzt.
- In-Video-Eskalation unverändert beibehalten.

## 0.6.0

- Kostenmodell für alle Erkennungsagenten ergänzt.
- Supervisor plant Agenten nach Sicherheit, Nutzen und Aufwand.
- Aktivierte und konfigurierte Online-Provider werden automatisch ausgeführt.
- Provider werden nach Medientyp und Priorität ausgewählt.
- Treffer verschiedener Quellen werden vereinheitlicht und gemeinsam bewertet.
- In-Video-Erkennung bleibt als verpflichtende Eskalationsstufe für unklare Fälle vorgesehen.


## 0.4.5

- Plugin-spezifische Cache-Verwaltung für das Plugin Center ergänzt.
- Gesamter Analyse-Cache kann nach Sicherheitsabfrage gelöscht werden.
- Anzahl gespeicherter Analysen und Pfad der Cache-Datenbank werden angezeigt.
- Eigene `create_window()`-Schnittstelle für zuverlässiges Öffnen als Desktop-Fenster ergänzt.
- `create_widget()` bleibt als Abwärtskompatibilität erhalten.

## 0.4.2

- Medienerkennung aus Datei- und Ordnernamen deutlich erweitert.
- Erkennt Filme anhand von Titel und Jahr sowie Serien in SxxExx-, 2x03- und deutschen Staffel-/Folgenformaten.
- Erkennt Mehrfachfolgen, Specials und absolute Episodennummern.
- Erkennt zahlreiche Schnittfassungen wie Extended, Director's Cut, Uncut, Unrated, IMAX, Final Cut und Remastered.
- Nutzt bei schwachen Dateinamen aussagekräftige Elternordner als zusätzlichen Titelkandidaten.
- Liefert nachvollziehbare Gründe, mehrere Editionskandidaten und einen Hinweis für erforderliche externe Recherche.
- Desktop- und Webanzeige für Mehrfachfolgen, Fassungen und Erkennungsgründe erweitert.

## 0.4.1

- Web-Wissenssuche ohne Query-Parameter neu umgesetzt.
- Weboberfläche lädt den lokalen Wissensindex über einen festen Endpunkt.
- Suche und Alias-Suche werden direkt im Browser ausgeführt.
- Dadurch ist die Funktion unabhängig von der Query-Auswertung des RequestContext.
- Desktop-Wissenssuche bleibt unverändert serverseitig.

## 0.4.0

- Erste Knowledge Engine ergänzt.


## 0.4.3

- Zentrale Tool-Suche für MediaHub_Tools erweitert.
- Cache-Zeitpunkt, gezieltes Löschen und erzwungene Neuanalyse vorbereitet.
- Weitere Release-Gruppen und Störbegriffe entfernt.
- Gemeinsamer, nicht ausführender Änderungsplan für Renamer und Metadata Editor ergänzt.
- Architektur für zusätzliche Medientypen wie Hörbücher vorbereitet.
## 0.4.4

- Tool-Zuordnung für den globalen MediaHub-Tools-Status korrigiert.
- MediaInfo, MKVToolNix und Tesseract werden jetzt gemeinsam über `required_tools` registriert.
- Optionale Werkzeuge bleiben mit `required: false` optional, werden aber trotzdem als vom KI-Assistenten verwendet angezeigt.
- Verhindert, dass installierte Plugin-Werkzeuge im globalen Tools-Status wieder verschwinden.


## 0.5.0

- Modulares Quellen-Manager-Grundsystem ergänzt.
- TMDb, TheTVDB und IMDb als deaktivierte, konfigurierbare Provider vorbereitet.
- Eigene API-Quellen und eigene Webseiten-Scanner über `config/sources.json` vorgesehen.
- Supervisor-Agent ergänzt, der Online- und In-Video-Tiefenanalyse anhand der lokalen Sicherheit plant.
- In-Video-Agent als verbindliche Pipeline für OCR, Untertitel, Audio, Fingerprints und Schnittfassungserkennung angelegt.
- Bestehende technische Analyse, Cache-Funktion, Desktop-Fenster und Plugin-Einstellungen bleiben erhalten.
