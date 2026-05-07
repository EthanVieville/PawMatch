import os
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="AdoptMe API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)

DATA_PATH = Path(os.getenv("DATA_PATH", "./data"))


def _load_animal(animal_dir: Path, species: str) -> dict:
    with open(animal_dir / "data.json", encoding="utf-8") as f:
        data = json.load(f)
    data["id"] = animal_dir.name
    data["species"] = species
    images = [
        f"/images/{species}/{animal_dir.name}/{img.name}"
        for img in sorted(animal_dir.glob("image_*.jpg"))
    ]
    if images:
        data["local_images"] = images
    return data


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/animals")
def list_animals(species: str = None):
    animals = []
    if not DATA_PATH.exists():
        return animals
    for species_dir in sorted(DATA_PATH.iterdir()):
        if not species_dir.is_dir():
            continue
        if species and species_dir.name != species:
            continue
        for animal_dir in sorted(species_dir.iterdir()):
            if not (animal_dir / "data.json").exists():
                continue
            try:
                animals.append(_load_animal(animal_dir, species_dir.name))
            except Exception:
                pass
    return animals


@app.get("/animals/{species}/{animal_id}")
def get_animal(species: str, animal_id: str):
    animal_dir = DATA_PATH / species / animal_id
    if not (animal_dir / "data.json").exists():
        raise HTTPException(status_code=404, detail="Animal not found")
    return _load_animal(animal_dir, species)


# Sert les images scrapées localement (utile en dev, remplacé par S3 en prod)
if DATA_PATH.exists():
    app.mount("/images", StaticFiles(directory=str(DATA_PATH)), name="images")
