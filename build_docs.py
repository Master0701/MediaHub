from src.mediahub.docs.builder import build_docs


# Windows/Terminal UTF-8 erzwingen, damit Emoji-Ausgaben beim Build nicht abstuerzen.
def _force_utf8_console():
    import os
    import sys
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_force_utf8_console()
def main():
    build_docs()


if __name__ == "__main__":
    main()
