from __future__ import annotations

"""Zentraler Katalog für portable MediaHub-Werkzeuge.

Downloadquellen, Archivtypen und Erkennungsdateien werden ausschließlich hier
gepflegt. ToolService übernimmt nur noch Download, Entpacken und Statusprüfung.
"""

SEVEN_ZIP_BOOTSTRAP = {
    "version": "26.02",
    "url": "https://github.com/ip7z/7zip/releases/download/26.02/7zr.exe",
    "filename": "7zr.exe",
    "license": "LGPL-2.1-or-later mit unRAR-Einschränkungen",
    "homepage": "https://www.7-zip.org/",
}

PLUGIN_TOOL_INSTALLS = {
    "mediainfo": {
        "download_page": "https://mediaarea.net/en/MediaInfo/Download/Windows",
        "asset_pattern": r"/download/binary/mediainfo/[0-9.]+/MediaInfo_CLI_[0-9.]+_Windows_x64\.zip",
        "archive_type": "zip",
        "search_names": ["mediainfo.exe", "MediaInfo.exe"],
    },
    "tesseract": {
        # Eigenes, aus dem offiziellen Tesseract-Quellcode gebautes
        # Windows-x64-Paket aus dem öffentlichen MediaHub_Tools-Repository.
        # Die Latest-Release-API hält MediaHub automatisch auf dem jeweils
        # aktuell veröffentlichten und geprüften Paketstand.
        "release_api": "https://api.github.com/repos/Master0701/MediaHub_Tools/releases/latest",
        "asset_pattern": r"^Tesseract-Projekt\.zip$",
        "archive_type": "github_zip",
        "search_names": ["tesseract.exe"],
    },
    "mkvtoolnix": {
        "download_page": "https://mkvtoolnix.download/downloads.html",
        "asset_pattern": r"(?:https?://mkvtoolnix\.download)?/windows/releases/[0-9.]+/mkvtoolnix-64-bit-[0-9.]+\.7z|mkvtoolnix-64-bit-[0-9.]+\.7z",
        "archive_type": "7z",
        # Sichere Rückfallquelle für den aktuell geprüften Stand. Wird nur
        # verwendet, falls die HTML-Struktur der Downloadseite geändert wurde.
        "fallback_urls": [
            "https://mkvtoolnix.download/windows/releases/100.0/mkvtoolnix-64-bit-100.0.7z",
        ],
        "search_names": ["mkvmerge.exe"],
    },
}
