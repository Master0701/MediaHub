from __future__ import annotations

import importlib
from pathlib import Path

from src.mediahub.tests.test_report import TestReport, TestResult

TEST_MODULES = [
    "src.mediahub.tests.test_project",
    "src.mediahub.tests.test_tools",
    "src.mediahub.tests.test_database",
    "src.mediahub.tests.test_settings",
    "src.mediahub.tests.test_downloads",
    "src.mediahub.tests.test_backup",
    "src.mediahub.tests.test_scheduler",
    "src.mediahub.tests.test_plugins",
    "src.mediahub.tests.test_docs_builder",
    "src.mediahub.tests.test_help",
]


class MediaHubTestRunner:
    def __init__(self, base_dir: Path, version: str = "unbekannt", mode: str = "quick"):
        self.base_dir = Path(base_dir)
        self.version = version
        self.mode = mode

    def run(self) -> TestReport:
        results: list[TestResult] = []
        for module_name in TEST_MODULES:
            try:
                module = importlib.import_module(module_name)
                run_tests = getattr(module, "run_tests")
                results.extend(run_tests(self.base_dir, self.mode))
            except Exception as exc:
                results.append(TestResult("Testsystem", module_name, "ERROR", f"Testmodul fehlgeschlagen: {exc}"))
        return TestReport(self.mode, self.version, results, self.base_dir)
