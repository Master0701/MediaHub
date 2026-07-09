"""
Neutraler Zugangsschutz fuer interne MediaHub-Werkzeuge.

Teil 8.2: Starkes Einmal-Passwort statt dauerhaftem Passwort.

Prinzip:
- MediaHub speichert nur eine lokale Gate-Datei unter config/.mh_gate.json.
- Diese Datei enthaelt ein zufaelliges Secret und einen Zaehler.
- Das Passwort-Tool berechnet daraus das naechste starke Einmal-Passwort.
- MediaHub akzeptiert jedes Passwort nur genau einmal und erhoeht danach den Zaehler.

Wichtig:
- Die Gate-Datei gehoert NICHT in Git.
- Wer die Gate-Datei UND das Generator-Tool hat, kann Codes erzeugen.
  Fuer ein lokales Desktop-Programm ist das ein guter Schutz vor versehentlichem Zugriff,
  aber kein absoluter Kopierschutz gegen jemanden mit vollem Dateizugriff.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from pathlib import Path
from typing import Any, Dict, Tuple

_GATE_FILE_NAME = ".mh_gate.json"
_SCHEMA = 3
_PASSWORD_LENGTH = 24
_PASSWORD_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#%&+-_?"
_LOOKAHEAD = 3


def gate_file(base_dir: Path | str) -> Path:
    return Path(base_dir) / "config" / _GATE_FILE_NAME


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + padding).encode("ascii"))


def _normalize_password(password: str) -> str:
    """Normalisiert nur kopierbedingte Leerzeichen, nicht die Passwortzeichen selbst."""
    return str(password or "").strip()


def _password_for(secret: bytes, counter: int) -> str:
    msg = f"MediaHub-Release-Assistent:{int(counter)}".encode("utf-8")
    digest = hmac.new(secret, msg, hashlib.sha512).digest()
    alphabet = _PASSWORD_ALPHABET
    chars = []
    block = digest
    round_no = 0
    while len(chars) < _PASSWORD_LENGTH:
        if round_no > 0:
            block = hmac.new(secret, msg + b":" + str(round_no).encode("ascii"), hashlib.sha512).digest()
        for byte in block:
            chars.append(alphabet[byte % len(alphabet)])
            if len(chars) >= _PASSWORD_LENGTH:
                break
        round_no += 1
    return "".join(chars)


def make_record() -> Dict[str, Any]:
    return {
        "schema": _SCHEMA,
        "kind": "counter_hmac_strong_otp",
        "secret": _b64e(secrets.token_bytes(32)),
        "counter": 0,
        "password_length": _PASSWORD_LENGTH,
        "lookahead": _LOOKAHEAD,
        "note": "Lokale MediaHub-Gate-Datei. Nicht in Git hochladen.",
    }


def save_record(base_dir: Path | str, record: Dict[str, Any]) -> Path:
    path = gate_file(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    return path


def load_record(base_dir: Path | str) -> Dict[str, Any] | None:
    path = gate_file(base_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def create_gate(base_dir: Path | str, force: bool = False) -> Path:
    path = gate_file(base_dir)
    if path.exists() and not force:
        raise FileExistsError(str(path))
    return save_record(base_dir, make_record())


def gate_exists(base_dir: Path | str) -> bool:
    return gate_file(base_dir).exists()


def _secret_from_record(record: Dict[str, Any]) -> bytes:
    return _b64d(str(record.get("secret") or ""))


def next_password(base_dir: Path | str) -> Tuple[str, int]:
    """Gibt den naechsten Einmal-Code zur Anzeige im externen Tool zurueck.

    Der Zaehler wird hier absichtlich NICHT erhoeht. Erst MediaHub verbraucht den Code.
    Dadurch kann das Tool erneut gestartet werden, falls man den Code nicht kopiert hat.
    """
    record = load_record(base_dir)
    if not record:
        raise FileNotFoundError(str(gate_file(base_dir)))
    secret = _secret_from_record(record)
    counter = int(record.get("counter") or 0) + 1
    return _password_for(secret, counter), counter


def verify_password(base_dir: Path | str, password: str) -> bool:
    """Prueft und verbraucht einen Einmal-Code."""
    normalized = _normalize_password(password)
    if len(normalized) < 12:
        return False

    record = load_record(base_dir)
    if not record:
        return False

    try:
        secret = _secret_from_record(record)
        current = int(record.get("counter") or 0)
        lookahead = int(record.get("lookahead") or _LOOKAHEAD)
    except Exception:
        return False

    for step in range(1, max(1, lookahead) + 1):
        candidate_counter = current + step
        expected = _password_for(secret, candidate_counter)
        if hmac.compare_digest(normalized, expected):
            record["counter"] = candidate_counter
            save_record(base_dir, record)
            return True

    return False
