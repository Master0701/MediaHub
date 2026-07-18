from pathlib import Path

from src.mediahub.services.tool_service import ToolService
from src.mediahub.tests.test_report import TestResult

TOOLS = ["yt-dlp", "ffmpeg", "ffprobe", "deno"]


def run_tests(base_dir: Path, mode: str):
    results = []
    tools_dir = base_dir / "tools"
    results.append(TestResult("Tools", "tools-Ordner", "OK" if tools_dir.exists() else "WARN", str(tools_dir)))
    service = ToolService(base_dir)
    for tool_id in TOOLS:
        local = service.tool_path(tool_id)
        status = "OK" if local.exists() else "WARN"
        results.append(TestResult("Tools", local.name, status, str(local) if local.exists() else "nicht gefunden"))
    return results
