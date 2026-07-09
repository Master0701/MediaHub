from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass
class TestResult:
    category: str
    name: str
    status: str
    message: str = ""
    details: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "OK"

    @property
    def warning(self) -> bool:
        return self.status == "WARN"

    @property
    def error(self) -> bool:
        return self.status == "ERROR"


class TestReport:
    def __init__(self, mode: str, version: str, results: Iterable[TestResult], base_dir: Path):
        self.mode = mode
        self.version = version
        self.results = list(results)
        self.base_dir = Path(base_dir)
        self.created = datetime.now()

    @property
    def ok_count(self) -> int:
        return sum(1 for result in self.results if result.ok)

    @property
    def warn_count(self) -> int:
        return sum(1 for result in self.results if result.warning)

    @property
    def error_count(self) -> int:
        return sum(1 for result in self.results if result.error)

    @property
    def total_count(self) -> int:
        return len(self.results)

    @property
    def release_ready(self) -> bool:
        return self.error_count == 0

    def as_text(self) -> str:
        lines = [
            "========================================",
            "MediaHub Selbsttest",
            "========================================",
            f"Version: {self.version}",
            f"Modus: {self.mode}",
            f"Erstellt: {self.created:%Y-%m-%d %H:%M:%S}",
            "",
        ]
        current_category = None
        for result in self.results:
            if result.category != current_category:
                current_category = result.category
                lines.append(f"[{current_category}]")
            marker = {"OK": "[OK]", "WARN": "[WARN]", "ERROR": "[FEHLER]"}.get(result.status, "[INFO]")
            line = f"{marker} {result.name}: {result.message}"
            lines.append(line)
            if result.details:
                for detail_line in str(result.details).splitlines():
                    lines.append(f"    {detail_line}")
        lines.extend([
            "",
            "========================================",
            f"Tests: {self.total_count}",
            f"OK: {self.ok_count}",
            f"Warnungen: {self.warn_count}",
            f"Fehler: {self.error_count}",
            f"Status: {'READY FOR RELEASE' if self.release_ready else 'NICHT FREIGEGEBEN'}",
            "========================================",
        ])
        return "\n".join(lines)

    def as_html(self) -> str:
        rows = []
        for result in self.results:
            css = result.status.lower()
            rows.append(
                "<tr class='{css}'><td>{category}</td><td>{name}</td><td>{status}</td><td>{message}</td></tr>".format(
                    css=css,
                    category=_escape(result.category),
                    name=_escape(result.name),
                    status=_escape(result.status),
                    message=_escape(result.message),
                )
            )
        return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>MediaHub Selbsttest</title>
<style>
body {{ font-family: Arial, sans-serif; background: #1e1e1e; color: #eeeeee; padding: 24px; }}
h1 {{ margin-bottom: 4px; }}
.summary {{ margin: 16px 0; padding: 12px; background: #2b2b2b; border-radius: 8px; }}
table {{ border-collapse: collapse; width: 100%; background: #252526; }}
th, td {{ border-bottom: 1px solid #3a3a3a; padding: 8px; text-align: left; }}
th {{ background: #333337; }}
.ok td:nth-child(3) {{ color: #7bd88f; font-weight: bold; }}
.warn td:nth-child(3) {{ color: #ffd166; font-weight: bold; }}
.error td:nth-child(3) {{ color: #ff6b6b; font-weight: bold; }}
</style>
</head>
<body>
<h1>MediaHub Selbsttest</h1>
<div>Version: {_escape(self.version)} · Modus: {_escape(self.mode)} · {self.created:%Y-%m-%d %H:%M:%S}</div>
<div class="summary">Tests: {self.total_count} · OK: {self.ok_count} · Warnungen: {self.warn_count} · Fehler: {self.error_count} · Status: {'READY FOR RELEASE' if self.release_ready else 'NICHT FREIGEGEBEN'}</div>
<table>
<thead><tr><th>Bereich</th><th>Test</th><th>Status</th><th>Meldung</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</body>
</html>"""

    def save(self) -> dict[str, Path]:
        logs_dir = self.base_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        stamp = self.created.strftime("%Y-%m-%d_%H-%M-%S")
        safe_mode = self.mode.lower().replace(" ", "_")
        text_path = logs_dir / f"selftest_{safe_mode}_{stamp}.txt"
        html_path = logs_dir / f"selftest_{safe_mode}_{stamp}.html"
        latest_txt = logs_dir / "selftest_latest.txt"
        latest_html = logs_dir / "selftest_latest.html"
        text = self.as_text()
        html = self.as_html()
        text_path.write_text(text, encoding="utf-8")
        html_path.write_text(html, encoding="utf-8")
        latest_txt.write_text(text, encoding="utf-8")
        latest_html.write_text(html, encoding="utf-8")
        return {"text": text_path, "html": html_path, "latest_text": latest_txt, "latest_html": latest_html}


def _escape(value) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
