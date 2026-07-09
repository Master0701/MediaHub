from pathlib import Path


class ArchiveService:
    def get_archive_path(self, channel) -> Path:
        work_dir = Path(channel.work_folder or "downloads/work") / channel.name
        return work_dir / "archive.txt"

    def load_downloaded_ids(self, channel) -> set[str]:
        archive_path = self.get_archive_path(channel)

        if not archive_path.exists():
            return set()

        downloaded_ids = set()

        with archive_path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split()

                if len(parts) >= 2:
                    downloaded_ids.add(parts[-1])

        return downloaded_ids

    def mark_videos(self, channel, videos: list[dict]) -> list[dict]:
        downloaded_ids = self.load_downloaded_ids(channel)

        for video in videos:
            video_id = video.get("id", "")

            if video_id in downloaded_ids:
                video["status"] = "Bereits geladen"
                video["checked"] = False
            else:
                video["status"] = "Neu"
                video["checked"] = True

        return videos