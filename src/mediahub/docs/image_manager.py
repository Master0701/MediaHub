import shutil
from pathlib import Path

from src.mediahub.docs.constants import IMAGE_SUFFIXES
from src.mediahub.docs.markdown_tools import MarkdownTools
from src.mediahub.docs.models import DocBook


class ImageManager:
    def __init__(self):
        self.tools = MarkdownTools()

    def resolve_image(self, book: DocBook, image_name: str) -> Path:
        image_name = image_name.strip()

        if image_name.startswith("images/"):
            image_name = image_name[len("images/"):]
        elif image_name.startswith("./images/"):
            image_name = image_name[len("./images/"):]

        if not Path(image_name).suffix:
            image_name += ".png"

        original = book.image_dir / image_name

        stem = Path(image_name).stem
        suffix = Path(image_name).suffix or ".png"
        marked = book.image_dir / "marked" / f"{stem}_marked{suffix}"

        if marked.exists():
            return marked

        return original

    def collect_figures(self, book: DocBook, docs):
        figures = []
        figure_no = 1

        for doc in docs:
            for line in doc["text"].splitlines():
                ref = self.tools.image_reference(line)

                if not ref:
                    continue

                image_name, caption = ref
                image_path = self.resolve_image(book, image_name)

                figures.append(
                    {
                        "number": figure_no,
                        "image_name": Path(image_name).name,
                        "caption": caption,
                        "path": image_path,
                        "exists": image_path.exists(),
                        "doc_key": doc["key"],
                        "doc_title": doc["title"],
                    }
                )

                figure_no += 1

        return figures

    def figure_lookup(self, figures):
        lookup = {}

        for fig in figures:
            name = fig["image_name"]
            lookup[(fig["doc_key"], name)] = fig
            lookup[(fig["doc_key"], Path(name).stem)] = fig
            lookup[(fig["doc_key"], f"images/{name}")] = fig

        return lookup

    def copy_images(self, book: DocBook, target_dir: Path):
        target_images = target_dir / "images"
        target_images.mkdir(parents=True, exist_ok=True)

        image_files = []

        for image in book.image_dir.glob("*.*"):
            if image.suffix.lower() in IMAGE_SUFFIXES:
                image_files.append(image)

        marked_dir = book.image_dir / "marked"
        if marked_dir.exists():
            for image in marked_dir.glob("*.*"):
                if image.suffix.lower() in IMAGE_SUFFIXES:
                    image_files.append(image)

        for image in image_files:
            shutil.copy2(image, target_images / image.name)
