from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocBook:
    key: str
    title: str
    source_dir: Path
    image_dir: Path
    app_dir: Path
    release_dir: Path
    txt_name: str
    html_name: str
    pdf_name: str
    docx_name: str
    index_name: str | None = None