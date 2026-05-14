"""
Compute and store sentence embeddings for all animals in the database.

Run locally (postgres must be accessible):
    pip install -r scripts/requirements.txt
    python scripts/compute_embeddings.py

    # Custom DB URL (e.g. via SSH tunnel to EC2):
    DATABASE_URL=postgresql://pawmatch:pawmatch@localhost:5432/pawmatch python scripts/compute_embeddings.py
"""

import os
import psycopg2
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://pawmatch:pawmatch@localhost:5432/pawmatch",
)

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384


def _build_text(animal: dict) -> str:
    """Combine structured fields into a single string to embed."""
    parts = []
    if animal["species"]:
        parts.append(animal["species"])
    if animal["race"]:
        parts.append(animal["race"])
    if animal["sex"] and animal["sex"] != "unknown":
        parts.append(animal["sex"])
    if animal["age"] is not None:
        parts.append(f"{animal['age']} ans")
    if animal["description"]:
        parts.append(animal["description"][:600])
    return " — ".join(parts) if parts else "animal"


def _migrate_column(conn):
    """Drop and recreate the embedding column with the correct dimension."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT atttypmod FROM pg_attribute pa
            JOIN pg_class pc ON pa.attrelid = pc.oid
            WHERE pc.relname = 'animals' AND pa.attname = 'embedding'
        """)
        row = cur.fetchone()
        current_dim = row[0] if row else None

        if current_dim != EMBEDDING_DIM:
            print(f"Migrating embedding column: {current_dim} → {EMBEDDING_DIM} dims")
            cur.execute("ALTER TABLE animals DROP COLUMN IF EXISTS embedding")
            cur.execute(f"ALTER TABLE animals ADD COLUMN embedding vector({EMBEDDING_DIM})")
            conn.commit()
            print("Migration done.")
        else:
            print(f"Embedding column already at {EMBEDDING_DIM} dims, no migration needed.")


def run():
    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    conn = psycopg2.connect(DATABASE_URL)
    try:
        _migrate_column(conn)

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, species, race, sex, age, description FROM animals ORDER BY scraped_at"
            )
            rows = cur.fetchall()

        animals = [
            dict(zip(["id", "species", "race", "sex", "age", "description"], r))
            for r in rows
        ]
        print(f"{len(animals)} animals to embed")

        texts = [_build_text(a) for a in animals]
        embeddings = model.encode(texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True)

        with conn.cursor() as cur:
            for animal, vec in tqdm(zip(animals, embeddings), total=len(animals), desc="Saving"):
                cur.execute(
                    "UPDATE animals SET embedding = %s WHERE id = %s",
                    (vec.tolist(), str(animal["id"])),
                )
        conn.commit()
        print(f"Done — {len(animals)} embeddings stored.")

    finally:
        conn.close()


if __name__ == "__main__":
    run()
