from pathlib import Path
import subprocess
import urllib.request
import zipfile
import shutil
import os


class ToolService:
    YT_DLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    DENO_URL = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"

    FFMPEG_URLS = [
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    ]

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.tools_dir = self.base_dir / "tools"

        self.yt_dlp = self.tools_dir / "yt-dlp.exe"
        self.ffmpeg = self.tools_dir / "ffmpeg.exe"
        self.ffprobe = self.tools_dir / "ffprobe.exe"
        self.deno = self.tools_dir / "deno.exe"

    def ensure_tools_dir(self):
        self.tools_dir.mkdir(parents=True, exist_ok=True)

    def check_tools(self) -> dict:
        self.ensure_tools_dir()
        return {
            "yt-dlp.exe": self.yt_dlp.exists(),
            "ffmpeg.exe": self.ffmpeg.exists(),
            "ffprobe.exe": self.ffprobe.exists(),
            "deno.exe": self.deno.exists(),
        }

    def missing_tools(self) -> list[str]:
        return [name for name, exists in self.check_tools().items() if not exists]

    def ffmpeg_location(self) -> str:
        return str(self.tools_dir)

    def open_tools_folder(self):
        self.ensure_tools_dir()
        os.startfile(self.tools_dir)

    def get_tool_versions(self) -> dict:
        return {
            "yt-dlp": self._get_version(self.yt_dlp, ["--version"]),
            "ffmpeg": self._get_version(self.ffmpeg, ["-version"], first_line_only=True),
            "ffprobe": self._get_version(self.ffprobe, ["-version"], first_line_only=True),
            "deno": self._get_version(self.deno, ["--version"], first_line_only=True),
        }

    def _get_version(self, exe_path: Path, args: list[str], first_line_only: bool = False) -> str:
        if not exe_path.exists():
            return "fehlt"

        try:
            result = subprocess.run(
                [str(exe_path), *args],
                capture_output=True,
                text=True,
                timeout=10
            )

            output = (result.stdout or result.stderr).strip()

            if first_line_only and output:
                return output.splitlines()[0]

            return output or "unbekannt"

        except Exception as error:
            return f"Fehler: {error}"

    def download_file(self, url: str, target: Path, log_callback=None, timeout: int = 300):
        part_file = target.with_suffix(target.suffix + ".part")

        if part_file.exists():
            part_file.unlink()

        request = urllib.request.Request(url, headers={"User-Agent": "MediaHub"})

        if log_callback:
            log_callback(f"Download: {url}")

        with urllib.request.urlopen(request, timeout=timeout) as response:
            with part_file.open("wb") as file:
                shutil.copyfileobj(response, file)

        if target.exists():
            target.unlink()

        part_file.rename(target)

    def download_missing_tools(self, log_callback=None):
        self.ensure_tools_dir()
        missing = self.missing_tools()

        if not missing:
            if log_callback:
                log_callback("Alle Tools sind bereits vorhanden.")
            return

        if "yt-dlp.exe" in missing:
            if log_callback:
                log_callback("Lade yt-dlp.exe herunter...")
            self.download_file(self.YT_DLP_URL, self.yt_dlp, log_callback)

        if "ffmpeg.exe" in missing or "ffprobe.exe" in missing:
            self.download_ffmpeg(log_callback)

        if "deno.exe" in missing:
            self.download_deno(log_callback)

        if log_callback:
            log_callback("Tool-Download abgeschlossen.")

    def redownload_all_tools(self, log_callback=None):
        self.ensure_tools_dir()

        for file in [self.yt_dlp, self.ffmpeg, self.ffprobe, self.tools_dir / "ffplay.exe", self.deno]:
            if file.exists():
                file.unlink()

        self.download_missing_tools(log_callback)


    def deno_path(self) -> str | None:
        if self.deno.exists():
            return str(self.deno)
        return None

    def download_deno(self, log_callback=None):
        zip_path = self.tools_dir / "deno.zip"
        extract_dir = self.tools_dir / "_deno_extract"

        if zip_path.exists():
            zip_path.unlink()

        if extract_dir.exists():
            shutil.rmtree(extract_dir)

        extract_dir.mkdir(parents=True, exist_ok=True)

        if log_callback:
            log_callback("Lade Deno herunter...")

        self.download_file(self.DENO_URL, zip_path, log_callback)

        if not zipfile.is_zipfile(zip_path):
            raise RuntimeError("Deno-Datei ist keine gültige ZIP-Datei.")

        if log_callback:
            log_callback("Entpacke Deno...")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        found = list(extract_dir.rglob("deno.exe"))
        if not found:
            raise RuntimeError("deno.exe wurde nach dem Entpacken nicht gefunden.")

        shutil.copy2(found[0], self.deno)

        zip_path.unlink(missing_ok=True)
        shutil.rmtree(extract_dir, ignore_errors=True)

        if log_callback:
            log_callback("deno.exe eingerichtet.")

    def download_ffmpeg(self, log_callback=None):
        zip_path = self.tools_dir / "ffmpeg.zip"
        last_error = None

        for url in self.FFMPEG_URLS:
            try:
                if zip_path.exists():
                    zip_path.unlink()

                if log_callback:
                    log_callback("Lade FFmpeg herunter...")

                self.download_file(url, zip_path, log_callback)

                if not zipfile.is_zipfile(zip_path):
                    raise RuntimeError("FFmpeg-Datei ist keine gültige ZIP-Datei.")

                self.extract_ffmpeg(zip_path, log_callback)

                if self.ffmpeg.exists() and self.ffprobe.exists():
                    if log_callback:
                        log_callback("FFmpeg erfolgreich eingerichtet.")
                    return

                raise RuntimeError("ffmpeg.exe oder ffprobe.exe wurde nach dem Entpacken nicht gefunden.")

            except Exception as error:
                last_error = error

                if log_callback:
                    log_callback(f"FFmpeg-Quelle fehlgeschlagen: {error}")

                if zip_path.exists():
                    zip_path.unlink()

        raise RuntimeError(f"FFmpeg konnte nicht heruntergeladen werden: {last_error}")

    def extract_ffmpeg(self, zip_path: Path, log_callback=None):
        extract_dir = self.tools_dir / "_ffmpeg_extract"

        if extract_dir.exists():
            shutil.rmtree(extract_dir)

        extract_dir.mkdir(parents=True, exist_ok=True)

        if log_callback:
            log_callback("Entpacke FFmpeg...")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        for file_name in ["ffmpeg.exe", "ffprobe.exe", "ffplay.exe"]:
            found = list(extract_dir.rglob(file_name))
            if found:
                shutil.copy2(found[0], self.tools_dir / file_name)

                if log_callback:
                    log_callback(f"{file_name} eingerichtet.")

        zip_path.unlink(missing_ok=True)
        shutil.rmtree(extract_dir, ignore_errors=True)