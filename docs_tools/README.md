# MediaHub Screenshot-Markierer

Dieses Werkzeug gehört nur zur Dokumentation.

Es verändert keine Originalbilder und hängt nicht direkt an `python build_docs.py`.

## Zweck

Aus:

```text
docs_source/user/images/01_startseite.png
```

wird zum Beispiel:

```text
docs_source/user/images/marked/01_startseite_marked.png
```

Die Originalbilder bleiben unverändert.

## Installation

Falls Pillow fehlt:

```bat
python -m pip install pillow
```

## Beispiel-Manifest erzeugen

```bat
python docs_tools\annotate_screenshot.py --create-example
```

Dadurch entsteht:

```text
docs_source\screenshot_annotations.json
```

## Markierte Bilder erzeugen

```bat
python docs_tools\annotate_screenshot.py
```

## Wichtig

`build_docs.py` bleibt unverändert.

Die markierten Bilder werden nur verwendet, wenn sie später im Markdown eingebunden werden, z. B.:

```markdown
![Startseite mit Markierungen](images/marked/01_startseite_marked.png)
```
