import json
import logging
import os

import requests
from slugify import slugify

logger = logging.getLogger(__name__)

# Explicit mapping avoids mimetypes platform inconsistencies
_CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def save_animal(data, category, base_path="data"):
    name_slug = slugify(data["name"])
    folder = os.path.join(base_path, category, name_slug)
    os.makedirs(folder, exist_ok=True)

    with open(os.path.join(folder, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    session = requests.Session()
    for i, img_url in enumerate(data.get("images", [])):
        try:
            response = session.get(img_url, timeout=10)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            ext = _CONTENT_TYPE_TO_EXT.get(content_type, ".jpg")

            img_path = os.path.join(folder, f"image_{i}{ext}")
            with open(img_path, "wb") as f:
                f.write(response.content)

            logger.debug("Saved image %d for %s (%s)", i, data["name"], ext)

        except requests.HTTPError as e:
            logger.warning("HTTP error downloading image %d for %s: %s", i, data["name"], e)
        except requests.RequestException as e:
            logger.warning("Network error downloading image %d for %s: %s", i, data["name"], e)
        except OSError as e:
            logger.error("Failed to write image %d for %s: %s", i, data["name"], e)
