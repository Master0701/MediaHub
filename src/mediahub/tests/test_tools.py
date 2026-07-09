import shutil
from pathlib import Path

from src.mediahub.tests.test_report import TestResult

TOOLS = ["yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe", "deno.exe"]


def run_tests(base_dir: Path, mode: str):
    results = []
    tools_dir = base_dir / "tools"
    results.append(TestResult("Tools", "tools-Ordner", "OK" if tools_dir.exists() else "WARN", str(tools_dir)))
    for tool in TOOLS:
        local = tools_dir / tool
        command_name = tool.replace(".exe", "")
        found = local.exists() or shutil.which(command_name) is not None or shutil.which(tool) is not None
        status = "OK" if found else "WARN"
        results.append(TestResult("Tools", tool, status, "gefunden" if found else "nicht gefunden"))
    return results
