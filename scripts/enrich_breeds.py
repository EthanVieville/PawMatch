# scripts/enrich_breeds.py
# Usage : python -m scripts.enrich_breeds
# Prérecquis : modèle entraîné dans dl_models/utils/out/pet_model_best.pth

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import glob
from tqdm import tqdm
from sqlalchemy import Column, String, Float, Integer, ForeignKey, create_engine
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, joinedload

from dl_models.predict import load_model, predict_from_url
from dl_models.utils.paths import OUT_PET_MODELS

# Connexion DB sans pgvector (on n'a pas besoin des embeddings ici)
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://pawmatch:pawmatch@localhost:5432/pawmatch",
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class AnimalImage(Base):
    __tablename__ = "animal_images"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    animal_id = Column(PG_UUID(as_uuid=True), ForeignKey("animals.id", ondelete="CASCADE"))
    url = Column(String)
    position = Column(Integer, default=0)
    animal = relationship("Animal", back_populates="images")


class Animal(Base):
    __tablename__ = "animals"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    species = Column(String)
    race = Column(String)
    race_predicted = Column(String)
    race_confidence = Column(Float)
    images = relationship(
        "AnimalImage", back_populates="animal",
        order_by="AnimalImage.position",
    )

CONFIDENCE_THRESHOLD = 0.70
SKIP_SPECIES = {"lapin"}


def _find_best_model() -> str:
    candidates = glob.glob(str(OUT_PET_MODELS / "pet_model_best.pth"))
    if not candidates:
        # Fallback sur le dernier modèle disponible
        candidates = glob.glob(str(OUT_PET_MODELS / "*.pth"))
    if not candidates:
        raise FileNotFoundError(
            f"Aucun modèle trouvé dans {OUT_PET_MODELS}. Lance d'abord python -m dl_models.train"
        )
    return max(candidates, key=os.path.getmtime)


def _migrate():
    """Ajoute les colonnes si elles n'existent pas (migration idempotente)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE animals ADD COLUMN IF NOT EXISTS race_predicted VARCHAR"))
        conn.execute(text("ALTER TABLE animals ADD COLUMN IF NOT EXISTS race_confidence FLOAT"))
        conn.commit()


def main():
    _migrate()

    model_path = _find_best_model()
    print(f"Modèle utilisé : {model_path}")
    model = load_model(model_path)

    db = SessionLocal()
    try:
        animals = (
            db.query(Animal)
            .options(joinedload(Animal.images))
            .filter(Animal.race.is_(None))
            .filter(Animal.race_predicted.is_(None))
            .all()
        )

        # Exclure lapins et animaux sans image
        to_process = [
            a for a in animals
            if a.species not in SKIP_SPECIES and a.images
        ]

        print(f"{len(animals)} animaux sans race | {len(to_process)} à traiter (avec image, hors lapins)")

        enriched = 0
        skipped_confidence = 0

        for animal in tqdm(to_process, desc="Prédiction races"):
            result = predict_from_url(model, animal.images[0].url)

            if result is None:
                continue

            if result["confidence"] >= CONFIDENCE_THRESHOLD:
                animal.race_predicted = result["breed"]
                animal.race_confidence = result["confidence"]
                enriched += 1
            else:
                skipped_confidence += 1

        db.commit()
        print(f"\nRésultat :")
        print(f"  Enrichis   : {enriched}")
        print(f"  Sous seuil : {skipped_confidence} (confiance < {CONFIDENCE_THRESHOLD:.0%})")

    finally:
        db.close()


if __name__ == "__main__":
    main()