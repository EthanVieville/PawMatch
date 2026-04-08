# scraper/storage.py

import os
import json
import requests
from slugify import slugify


def save_animal(data, category, base_path="data"):
    name_slug = slugify(f"{data['name']}")

    folder = os.path.join(base_path, category, name_slug)

    os.makedirs(folder, exist_ok=True)

    # JSON
    with open(os.path.join(folder, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # image principale
    for i, img_url in enumerate(data.get("images", [])):
        try:
            img_data = requests.get(img_url, timeout=10).content

            with open(os.path.join(folder, f"image_{i}.jpg"), "wb") as f:
                f.write(img_data)

        except:
            pass