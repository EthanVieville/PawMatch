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

from chat import stream_chat
from database import Animal, Refuge, get_db, init_db

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
    refuges = db.query(Refuge).filter(Refuge.lat.isnot(None)).all()
    return [
        {"name": r.name, "source": r.source, "lat": r.lat, "lng": r.lng}
        for r in refuges
    ]


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
