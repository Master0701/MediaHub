from __future__ import annotations

import sys
from pathlib import Path


def qr_matrix(text: str) -> list[list[bool]]:
    vendor = Path(__file__).resolve().parent / "vendor"
    value = str(vendor)
    if value not in sys.path:
        sys.path.insert(0, value)
    import qrcode  # type: ignore

    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=1, border=4)
    qr.add_data(text)
    qr.make(fit=True)
    return [[bool(cell) for cell in row] for row in qr.get_matrix()]
