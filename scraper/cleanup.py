"""
Cleanup script — validates stored animal URLs and removes dead listings.

A URL is considered dead if:
  - It redirects to the source's listing page (animal removed from site)
  - It returns HTTP 404
"""
import logging
import os
import uuid

import psycopg2
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://pawmatch:pawmatch@localhost:5432/pawmatch",
)
CLEANUP_SOURCE = os.environ.get("CLEANUP_SOURCE", "la-spa")

# Final URLs that indicate the animal listing page was removed
_DEAD_REDIRECT_SUFFIXES = [
    "la-spa.fr/adoption/",
    "la-spa.fr/adoption",
    "secondechance.org/",
]

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "PawMatch-Cleanup/1.0"})


def _connect():
    return psycopg2.connect(DATABASE_URL)


def _is_dead(url: str) -> bool:
    try:
        resp = _SESSION.get(url, timeout=15, allow_redirects=True)
        final = resp.url.rstrip("/")
        for suffix in _DEAD_REDIRECT_SUFFIXES:
            if final.endswith(suffix.rstrip("/")):
                return True
        return resp.status_code == 404
    except requests.RequestException as exc:
        logger.warning("Network error checking %s: %s", url, exc)
        return False


def init_db():
    conn = _connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cleanup_runs (
                        id              UUID PRIMARY KEY,
                        run_at          TIMESTAMP DEFAULT NOW(),
                        source          VARCHAR NOT NULL,
                        animals_checked INTEGER NOT NULL DEFAULT 0,
                        animals_removed INTEGER NOT NULL DEFAULT 0,
                        removed_names   TEXT[]  DEFAULT '{}'
                    )
                """)
    finally:
        conn.close()


def run_cleanup(source: str) -> dict:
    conn = _connect()
    try:
        # Step 1 — fetch all animals (read-only, commit immediately)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, source_url, name FROM animals WHERE source = %s",
            (source,),
        )
        animals = cur.fetchall()
        cur.close()
        conn.commit()

        checked = len(animals)
        removed_names = []
        dead_ids = []

        logger.info("Checking %d animals from source=%s …", checked, source)

        # Step 2 — check URLs outside any DB transaction (network I/O)
        for animal_id, source_url, name in animals:
            if _is_dead(source_url):
                logger.info("Dead listing — removing: %s (%s)", name, source_url)
                dead_ids.append(animal_id)
                removed_names.append(name)

        # Step 3 — delete dead animals + log run in a single transaction
        cur = conn.cursor()
        try:
            for animal_id in dead_ids:
                cur.execute("DELETE FROM animals WHERE id = %s", (animal_id,))

            cur.execute("""
                INSERT INTO cleanup_runs
                    (id, source, animals_checked, animals_removed, removed_names)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                str(uuid.uuid4()),
                source,
                checked,
                len(removed_names),
                removed_names,
            ))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

        logger.info(
            "Cleanup done — source=%s checked=%d removed=%d",
            source, checked, len(removed_names),
        )
        return {
            "source": source,
            "checked": checked,
            "removed": len(removed_names),
            "removed_names": removed_names,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    sources = [s.strip() for s in CLEANUP_SOURCE.split(",") if s.strip()]
    init_db()
    for src in sources:
        run_cleanup(src)
