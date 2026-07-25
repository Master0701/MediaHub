from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AnalysisCache:
    """Speichert vollständige Analyseergebnisse für unveränderte Dateien."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)

    @staticmethod
    def file_signature(path: Path) -> tuple[str, int, int]:
        stat = path.stat()
        return str(path.resolve()), int(stat.st_size), int(stat.st_mtime_ns)

    def get(self, path: Path) -> dict[str, Any] | None:
        file_path, size, modified_ns = self.file_signature(path)
        if not self.database_path.exists(): return None
        with sqlite3.connect(self.database_path, timeout=5.0) as db:
            db.row_factory = sqlite3.Row; self._ensure_payload_column(db)
            row = db.execute("SELECT analysis_payload, analyzed_at FROM identification_cache WHERE file_path=? AND file_size=? AND modified_ns=? LIMIT 1", (file_path,size,modified_ns)).fetchone()
        if not row or not row['analysis_payload']: return None
        try: result=json.loads(row['analysis_payload'])
        except (TypeError,ValueError,json.JSONDecodeError): return None
        result['cache']={"hit":True,"message":"Unveränderte Datei – gespeichertes Analyseergebnis verwendet.","analyzed_at":row['analyzed_at']}
        return result

    def put(self, path: Path, result: dict[str, Any]) -> None:
        file_path,size,modified_ns=self.file_signature(path)
        payload=json.dumps(result,ensure_ascii=False,separators=(",",":"))
        with sqlite3.connect(self.database_path,timeout=10.0) as db:
            self._ensure_payload_column(db)
            db.execute("""INSERT INTO identification_cache(file_path,file_size,modified_ns,confidence,method_summary,analysis_payload,analyzed_at)
            VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(file_path,file_size,modified_ns) DO UPDATE SET confidence=excluded.confidence,method_summary=excluded.method_summary,analysis_payload=excluded.analysis_payload,analyzed_at=CURRENT_TIMESTAMP""",
            (file_path,size,modified_ns,float((result.get('identification') or {}).get('confidence') or 0.0),', '.join(result.get('methods_used') or []),payload))
            db.commit()

    def delete(self, path: Path) -> int:
        file_path=str(Path(path).resolve())
        if not self.database_path.exists(): return 0
        with sqlite3.connect(self.database_path,timeout=5.0) as db:
            cur=db.execute('DELETE FROM identification_cache WHERE file_path=?',(file_path,)); db.commit(); return cur.rowcount

    def clear(self) -> int:
        if not self.database_path.exists(): return 0
        with sqlite3.connect(self.database_path,timeout=5.0) as db:
            cur=db.execute('DELETE FROM identification_cache'); db.commit(); return cur.rowcount

    @staticmethod
    def _ensure_payload_column(db: sqlite3.Connection) -> None:
        columns={row[1] for row in db.execute('PRAGMA table_info(identification_cache)').fetchall()}
        if 'analysis_payload' not in columns:
            db.execute('ALTER TABLE identification_cache ADD COLUMN analysis_payload TEXT'); db.commit()
