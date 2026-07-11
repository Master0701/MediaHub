"""Zentrale Build-Helfer für die MediaHub-Version.

Die einzige manuell gepflegte Versionsquelle ist:
    src/mediahub/app_info.py -> APP_VERSION
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_INFO_FILE = ROOT / "src" / "mediahub" / "app_info.py"
VERSION_INFO_FILE = ROOT / "version_info.txt"
INSTALLER_VERSION_FILE = ROOT / "installer" / "version_generated.iss"


def _read_constants() -> dict[str, str]:
    tree = ast.parse(APP_INFO_FILE.read_text(encoding="utf-8"), filename=str(APP_INFO_FILE))
    values: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            values[target.id] = node.value.value
    return values


_INFO = _read_constants()
APP_NAME = _INFO.get("APP_NAME", "MediaHub")
APP_VERSION = _INFO["APP_VERSION"]
APP_AUTHOR = _INFO.get("APP_AUTHOR", "MediaHub")
APP_DESCRIPTION = _INFO.get("APP_DESCRIPTION", "MediaHub")
APP_COPYRIGHT = _INFO.get("APP_COPYRIGHT", "Copyright © 2026 MediaHub")


def version_tuple(version: str = APP_VERSION) -> tuple[int, int, int, int]:
    numeric = version.split("-", 1)[0].split("+", 1)[0]
    parts = [int(part) for part in numeric.split(".") if part.isdigit()]
    return tuple((parts + [0, 0, 0, 0])[:4])  # type: ignore[return-value]


def write_version_info(path: Path = VERSION_INFO_FILE) -> Path:
    file_version = ".".join(str(part) for part in version_tuple())
    numbers = ", ".join(str(part) for part in version_tuple())
    content = f'''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({numbers}),
    prodvers=({numbers}),
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        "040704B0",
        [
          StringStruct("CompanyName", "{APP_AUTHOR}"),
          StringStruct("FileDescription", "{APP_DESCRIPTION}"),
          StringStruct("FileVersion", "{file_version}"),
          StringStruct("InternalName", "{APP_NAME}"),
          StringStruct("LegalCopyright", "{APP_COPYRIGHT}"),
          StringStruct("OriginalFilename", "{APP_NAME}.exe"),
          StringStruct("ProductName", "{APP_NAME}"),
          StringStruct("ProductVersion", "{file_version}")
        ]
      )
    ]),
    VarFileInfo([
      VarStruct("Translation", [1031, 1200])
    ])
  ]
)'''
    path.write_text(content, encoding="utf-8")
    return path


def write_installer_version(path: Path = INSTALLER_VERSION_FILE) -> Path:
    content = (
        "; Automatisch erzeugt aus src/mediahub/app_info.py. Nicht manuell bearbeiten.\n"
        f'#define MyAppName "{APP_NAME}"\n'
        f'#define MyAppVersion "{APP_VERSION}"\n'
        f'#define MyAppPublisher "{APP_AUTHOR}"\n'
        f'#define MyAppExeName "{APP_NAME}.exe"\n'
        f'#define MyAppSetupName "{APP_NAME}_Setup_v{APP_VERSION}"\n'
    )
    path.write_text(content, encoding="utf-8")
    return path


def prepare_version_files() -> None:
    write_version_info()
    write_installer_version()


if __name__ == "__main__":
    prepare_version_files()
    print(f"{APP_NAME} v{APP_VERSION}")
