import logging
import os
import uuid

import psycopg2
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://pawmatch:pawmatch@localhost:5432/pawmatch",
)
SOURCE = os.environ.get("SCRAPER_SOURCE", "la-spa")


def _connect():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Crée les tables si elles n'existent pas. Idempotent."""
    conn = _connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS animals (
                        id           UUID PRIMARY KEY,
                        source       VARCHAR NOT NULL,
                        source_url   VARCHAR NOT NULL,
                        name         VARCHAR NOT NULL,
                        species      VARCHAR,
                        race         VARCHAR,
                        sex          VARCHAR,
                        birth_date   VARCHAR,
                        age          INTEGER,
                        refuge       VARCHAR,
                        description  TEXT,
                        incompatibilities TEXT[],
                        scraped_at   TIMESTAMP DEFAULT NOW(),
                        UNIQUE(source, source_url)
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS animal_images (
                        id         UUID PRIMARY KEY,
                        animal_id  UUID REFERENCES animals(id) ON DELETE CASCADE,
                        url        VARCHAR NOT NULL,
                        position   INTEGER DEFAULT 0
                    )
                """)
    finally:
        conn.close()


def save_animal(data):
    """Upsert un animal et ses images en base. Relancer le scraper ne crée pas de doublons."""
    conn = _connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO animals (
                        id, source, source_url, name, species, race, sex,
                        birth_date, age, refuge, description, incompatibilities
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source, source_url) DO UPDATE SET
                        name              = EXCLUDED.name,
                        species           = EXCLUDED.species,
                        race              = EXCLUDED.race,
                        sex               = EXCLUDED.sex,
                        birth_date        = EXCLUDED.birth_date,
                        age               = EXCLUDED.age,
                        refuge            = EXCLUDED.refuge,
                        description       = EXCLUDED.description,
                        incompatibilities = EXCLUDED.incompatibilities,
                        scraped_at        = NOW()
                    RETURNING id
                """, (
                    str(uuid.uuid4()),
                    SOURCE,
                    data["url"],
                    data["name"],
                    data.get("species") or "inconnu",
                    data.get("race"),
                    data.get("sex"),
                    data.get("birth_date"),
                    data.get("age"),
                    data.get("refuge"),
                    data.get("description"),
                    data.get("incompatibilities", []),
                ))

                animal_id = cur.fetchone()[0]

                # Remplace les images à chaque scrape (évite les doublons d'URLs)
                cur.execute("DELETE FROM animal_images WHERE animal_id = %s", (animal_id,))

                images = data.get("images", [])
                if images:
                    execute_values(cur, """
                        INSERT INTO animal_images (id, animal_id, url, position)
                        VALUES %s
                    """, [
                        (str(uuid.uuid4()), animal_id, url, i)
                        for i, url in enumerate(images)
                    ])

        logger.debug("Saved %s (id=%s, images=%d)", data["name"], animal_id, len(images))
    except Exception as e:
        logger.error("Failed to save %s: %s", data.get("name"), e)
        raise
    finally:
        conn.close()
