import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import Animal, get_db, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PawMatch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _animal_to_dict(animal: Animal) -> dict:
    return {
        "id": str(animal.id),
        "source": animal.source,
        "source_url": animal.source_url,
        "name": animal.name,
        "species": animal.species,
        "race": animal.race,
        "sex": animal.sex,
        "birth_date": animal.birth_date,
        "age": animal.age,
        "refuge": animal.refuge,
        "description": animal.description,
        "incompatibilities": animal.incompatibilities or [],
        "scraped_at": animal.scraped_at.isoformat() if animal.scraped_at else None,
        "images": [img.url for img in animal.images],
    }


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "degraded", "db": "unavailable", "detail": str(e)}


@app.get("/animals")
def list_animals(
    species: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Animal)
    if species:
        query = query.filter(Animal.species == species)
    if source:
        query = query.filter(Animal.source == source)
    return [_animal_to_dict(a) for a in query.all()]


@app.get("/animals/{animal_id}")
def get_animal(animal_id: str, db: Session = Depends(get_db)):
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")
    return _animal_to_dict(animal)
