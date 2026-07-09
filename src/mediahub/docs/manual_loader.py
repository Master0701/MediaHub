from __future__ import annotations

from pathlib import Path

from src.mediahub.docs.help_loader import HelpLoader


def load_manual_text_entry(
    loader: HelpLoader,
    book: str,
    folder: str,
    txt_name: str,
) -> dict | None:
    doc = loader.first_existing_doc(f"{folder}/{txt_name}")

    if doc is None:
        return None

    try:
        text = doc.read_text(encoding="utf-8")
    except Exception:
        return None

    title = "Kurzanleitung" if book == "quick" else "Entwicklerhandbuch"

    return {
        "title": title,
        "raw_title": title,
        "key": book,
        "book": book,
        "keywords": text.lower(),
        "text": text,
        "source": str(Path(folder) / txt_name),
    }


def load_extra_manual_entries(loader: HelpLoader) -> list[dict]:
    entries = []

    quick = load_manual_text_entry(
        loader,
        "quick",
        "quick",
        "KURZANLEITUNG.txt",
    )

    if quick is not None:
        entries.append(quick)

    developer = load_manual_text_entry(
        loader,
        "developer",
        "developer",
        "ENTWICKLERHANDBUCH.txt",
    )

    if developer is not None:
        entries.append(developer)

    return entries