import re


# Alte MediaHub-Syntax:
# [[IMAGE:datei.png|Bildtitel]]
IMAGE_TOKEN = re.compile(r"\[\[IMAGE:([a-zA-Z0-9_\-./ äöüÄÖÜß]+)(?:\|([^\]]+))?\]\]")

# Normale Markdown-Syntax:
# ![Bildtitel](images/datei.png)
MARKDOWN_IMAGE_TOKEN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

IMAGE_SUFFIXES = [".png", ".jpg", ".jpeg", ".webp"]
