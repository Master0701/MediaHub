class ProfileService:
    PROFILES = {
        "Plex": {
            "audio_only": False,
            "container": "MKV",
            "resolution": "1080p",
            "audio_format": "M4A",
            "create_nfo": True,
            "create_poster": True,
            "create_fanart": True,
        },
        "Archiv": {
            "audio_only": False,
            "container": "MKV",
            "resolution": "Beste",
            "audio_format": "M4A",
            "create_nfo": True,
            "create_poster": True,
            "create_fanart": True,
        },
        "Mobil": {
            "audio_only": False,
            "container": "MP4",
            "resolution": "720p",
            "audio_format": "AAC",
            "create_nfo": False,
            "create_poster": True,
            "create_fanart": False,
        },
        "Audio": {
            "audio_only": True,
            "container": "MP4",
            "resolution": "Beste",
            "audio_format": "MP3",
            "create_nfo": False,
            "create_poster": True,
            "create_fanart": False,
        },
    }

    @classmethod
    def names(cls):
        return list(cls.PROFILES.keys())

    @classmethod
    def get(cls, name: str):
        return cls.PROFILES.get(name, cls.PROFILES["Plex"])