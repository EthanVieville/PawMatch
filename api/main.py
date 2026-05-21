import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import boto3
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from chat import stream_chat, _get_encoder
from database import Animal, Refuge, get_db, init_db

# ── Synonym mapping pour la recherche intelligente ────────────────────────────
_SPECIES_SYNONYMS: dict[str, str] = {
    "chien": "chien", "chiens": "chien", "toutou": "chien", "cabot": "chien",
    "dog": "chien", "canin": "chien", "canins": "chien",
    "chat": "chat", "chats": "chat", "minou": "chat", "minette": "chat",
    "félin": "chat", "félins": "chat", "cat": "chat",
    "lapin": "lapin", "lapins": "lapin", "rabbit": "lapin", "clapier": "lapin",
}

_SEX_SYNONYMS: dict[str, str] = {
    "male": "male", "mâle": "male", "mâles": "male", "males": "male",
    "garçon": "male", "garcons": "male", "m": "male",
    "femelle": "femelle", "femelles": "femelle",
    "fille": "femelle", "filles": "femelle", "f": "femelle",
}

_STOP_WORDS = {"un", "une", "des", "les", "le", "la", "de", "du", "et", "ou", "avec"}


def _parse_smart_search(
    raw: str,
    species_in: Optional[str],
    sex_in: Optional[str],
) -> tuple[Optional[str], Optional[str], str]:
    """
    Parse la requête libre pour en extraire espèce/sexe implicites.
    Retourne (species, sex, remaining_text) — les filtres explicites ont priorité.
    """
    species_out = species_in
    sex_out = sex_in
    leftover: list[str] = []

    for word in raw.lower().split():
        clean = word.strip(",.!?;:")
        if clean in _STOP_WORDS:
            continue
        if not species_out and clean in _SPECIES_SYNONYMS:
            species_out = _SPECIES_SYNONYMS[clean]
        elif not sex_out and clean in _SEX_SYNONYMS:
            sex_out = _SEX_SYNONYMS[clean]
        else:
            leftover.append(clean)

    return species_out, sex_out, " ".join(leftover)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.bedrock = boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION", "eu-west-1"),
    )
    from chat import _get_encoder
    _get_encoder()  # pre-load embedding model so first request isn't slow
    yield


app = FastAPI(title="PawMatch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
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


@app.get("/refuges")
def list_refuges(db: Session = Depends(get_db)):
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload
    from collections import defaultdict

    refuges = db.query(Refuge).filter(Refuge.lat.isnot(None)).all()
    if not refuges:
        return []

    names = [r.name for r in refuges]

    # 1 requête : counts groupés par refuge
    counts: dict[str, int] = dict(
        db.query(Animal.refuge, func.count(Animal.id))
        .filter(Animal.refuge.in_(names))
        .group_by(Animal.refuge)
        .all()
    )

    # 1-2 requêtes : animaux + images en eager load (joinedload évite le N+1)
    animals = (
        db.query(Animal)
        .options(joinedload(Animal.images))
        .filter(Animal.refuge.in_(names))
        .all()
    )

    thumbnails: dict[str, list[str]] = defaultdict(list)
    for a in animals:
        if a.refuge and a.images and len(thumbnails[a.refuge]) < 3:
            thumbnails[a.refuge].append(a.images[0].url)

    return [
        {
            "name": r.name,
            "source": r.source,
            "lat": r.lat,
            "lng": r.lng,
            "animal_count": counts.get(r.name, 0),
            "thumbnails": thumbnails.get(r.name, []),
        }
        for r in refuges
    ]


@app.get("/animals")
def list_animals(
    species: Optional[str] = None,
    sex: Optional[str] = None,
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    refuge: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 25,
    db: Session = Depends(get_db),
):
    # Extraire espèce/sexe implicites de la recherche libre (ex: "chien garçon")
    if search:
        species, sex, search = _parse_smart_search(search, species, sex)

    query = db.query(Animal)
    if species:
        query = query.filter(Animal.species == species)
    if sex:
        query = query.filter(Animal.sex == sex)
    if age_min is not None:
        query = query.filter(Animal.age >= age_min)
    if age_max is not None:
        query = query.filter(Animal.age <= age_max)
    if refuge:
        query = query.filter(Animal.refuge.ilike(f"%{refuge}%"))
    if source:
        query = query.filter(Animal.source == source)
    use_semantic = False
    if search:
        # Si des animaux ont des embeddings, on fait une recherche sémantique
        has_embeddings = db.query(Animal.id).filter(Animal.embedding.isnot(None)).first()
        if has_embeddings:
            use_semantic = True
            query_vec = _get_encoder().encode(search).tolist()
            query = query.filter(Animal.embedding.isnot(None))
        else:
            term = f"%{search}%"
            query = query.filter(Animal.name.ilike(term) | Animal.race.ilike(term))

    total = query.count()
    offset = (page - 1) * limit
    if use_semantic:
        items = (
            query
            .order_by(Animal.embedding.cosine_distance(query_vec))
            .offset(offset)
            .limit(limit)
            .all()
        )
    else:
        items = query.order_by(Animal.scraped_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [_animal_to_dict(a) for a in items],
    }


@app.get("/animals/{animal_id}")
def get_animal(animal_id: str, db: Session = Depends(get_db)):
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")
    return _animal_to_dict(animal)


@app.get("/animals/{animal_id}/similar")
def get_similar_animals(animal_id: str, limit: int = 6, db: Session = Depends(get_db)):
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")
    if animal.embedding is None:
        return []
    similar = (
        db.query(Animal)
        .filter(Animal.id != animal.id, Animal.embedding.isnot(None))
        .order_by(Animal.embedding.cosine_distance(animal.embedding))
        .limit(limit)
        .all()
    )
    return [_animal_to_dict(a) for a in similar]


class ChatRequest(BaseModel):
    message: str
    animal_id: Optional[str] = None
    history: list[dict] = []


@app.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    return StreamingResponse(
        stream_chat(
            message=request.message,
            history=request.history,
            animal_id=request.animal_id,
            db=db,
            bedrock_client=app.state.bedrock,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/chat/test")
def chat_test():
    """Debug endpoint: verifies Bedrock connectivity and IAM credentials."""
    import json as _json
    from chat import BEDROCK_MODEL
    try:
        resp = app.state.bedrock.invoke_model(
            modelId=BEDROCK_MODEL,
            body=_json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
            }),
        )
        result = _json.loads(resp["body"].read())
        return {"status": "ok", "model": BEDROCK_MODEL, "response": result}
    except Exception as e:
        return {"status": "error", "model": BEDROCK_MODEL, "detail": str(e), "type": type(e).__name__}
