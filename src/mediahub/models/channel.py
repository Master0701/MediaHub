from dataclasses import dataclass, asdict, field


@dataclass
class Channel:
    name: str
    url: str

    channel_id: str = ""
    description: str = ""

    profile: str = "Plex"
    audio_only: bool = False

    filename_template: str = "{title} S{season:02}E{episode:02}"

    work_folder: str = ""
    target_folder: str = ""

    poster: str = ""
    fanart: str = ""

    container: str = "MKV"
    resolution: str = "1080p"
    audio_format: str = "M4A"

    create_nfo: bool = True
    create_poster: bool = True
    create_fanart: bool = True
    clean_work_folder: bool = True

    playlist_folder_mode: str = "Nur Staffeln"

    # Neu: dauerhafte Playlist-Verwaltung
    playlist_settings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Channel":
        return Channel(
            name=data.get("name", ""),
            url=data.get("url", ""),
            channel_id=data.get("channel_id", data.get("id", "")),
            description=data.get("description", ""),
            profile=data.get("profile", "Plex"),
            audio_only=data.get("audio_only", False),
            filename_template=data.get(
                "filename_template",
                "{title} S{season:02}E{episode:02}"
            ),
            work_folder=data.get("work_folder", ""),
            target_folder=data.get("target_folder", ""),
            poster=data.get("poster", ""),
            fanart=data.get("fanart", ""),
            container=data.get("container", "MKV"),
            resolution=data.get("resolution", "1080p"),
            audio_format=data.get("audio_format", "M4A"),
            create_nfo=data.get("create_nfo", True),
            create_poster=data.get("create_poster", True),
            create_fanart=data.get("create_fanart", True),
            clean_work_folder=data.get("clean_work_folder", True),
            playlist_folder_mode=data.get("playlist_folder_mode", "Nur Staffeln"),
            playlist_settings=data.get("playlist_settings", []),
        )