#!/usr/bin/env python3
"""Job ponctuel : réécrit les descriptions d'animaux via Bedrock (Claude Haiku).

Chaque description brute de scraping est reformulée de façon claire et chaleureuse,
puis stockée dans la colonne `description_rewritten` de la table `animals`.
Chaque appel est tracé dans `llm_traces` (feature = description_rewrite).

Usage :
    python -m scripts.rewrite_descriptions
    python -m scripts.rewrite_descriptions --limit 50
    python -m scripts.rewrite_descriptions --dry-run       # affiche sans écrire
    python -m scripts.rewrite_descriptions --reset         # réécrit TOUS (déjà faits inclus)
"""

import argparse
import json
import logging
import os
import time
import uuid

import boto3
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pawmatch:pawmatch@localhost:5432/pawmatch")
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "eu.anthropic.claude-haiku-4-5-20251001-v1:0")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

_PRICING = {
    "haiku":  (0.80,  4.00),
    "sonnet": (3.00,  15.00),
    "opus":   (15.00, 75.00),
}

REWRITE_PROMPT = """\
Tu es un rédacteur bienveillant pour une plateforme française d'adoption animale.

Réécris la description suivante de façon claire, chaleureuse et engageante (3 à 5 phrases).
Règles :
- Supprime les informations redondantes, administratives ou inutiles (vaccins, puces, etc.)
- Mets en valeur le caractère et les besoins de l'animal
- Utilise un ton accessible et humain
- Réponds UNIQUEMENT avec la description réécrite, sans introduction ni commentaire

Description originale :
{description}"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    tier = next((k for k in _PRICING if k in model_id.lower()), "haiku")
    inp, out = _PRICING[tier]
    return (input_tokens * inp + output_tokens * out) / 1_000_000


def rewrite_one(bedrock, description: str) -> tuple[str, int, int, int]:
    """Retourne (texte_réécrit, input_tokens, output_tokens, latency_ms)."""
    start = time.time()
    resp = bedrock.invoke_model(
        modelId=BEDROCK_MODEL,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{
                "role": "user",
                "content": REWRITE_PROMPT.format(description=description[:2000]),
            }],
            "max_tokens": 512,
            "temperature": 0.3,
        }),
    )
    result = json.loads(resp["body"].read())
    latency_ms = int((time.time() - start) * 1000)
    text = result["content"][0]["text"].strip()
    usage = result.get("usage", {})
    return text, usage.get("input_tokens", 0), usage.get("output_tokens", 0), latency_ms


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",   type=int, default=0,     help="Nombre max d'animaux à traiter (0 = tous)")
    parser.add_argument("--dry-run", action="store_true",     help="Affiche sans écrire en base")
    parser.add_argument("--reset",   action="store_true",     help="Réécrit même les animaux déjà traités")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Sélection des animaux à traiter
    where = "" if args.reset else "AND description_rewritten IS NULL"
    limit_sql = f"LIMIT {args.limit}" if args.limit > 0 else ""
    cur.execute(f"""
        SELECT id, name, species, description
        FROM animals
        WHERE description IS NOT NULL AND description != '' {where}
        ORDER BY scraped_at DESC
        {limit_sql}
    """)
    animals = cur.fetchall()

    if not animals:
        logger.info("Aucun animal à traiter.")
        conn.close()
        return

    logger.info("%d animaux à réécrire (dry_run=%s)", len(animals), args.dry_run)

    bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    total_cost = 0.0
    total_input = 0
    total_output = 0
    errors = 0

    for i, animal in enumerate(animals, 1):
        animal_id = str(animal["id"])
        name = animal["name"]
        desc = animal["description"]

        logger.info("[%d/%d] %s (%s) — %d chars", i, len(animals), name, animal_id[:8], len(desc))

        try:
            rewritten, inp, out, latency_ms = rewrite_one(bedrock, desc)
            cost = _compute_cost(BEDROCK_MODEL, inp, out)
            total_cost += cost
            total_input += inp
            total_output += out

            if args.dry_run:
                print(f"\n--- {name} ---\nORIGINAL : {desc[:200]}...\nREWRITE  : {rewritten}\n")
            else:
                cur.execute(
                    "UPDATE animals SET description_rewritten = %s WHERE id = %s",
                    (rewritten, animal_id),
                )
                cur.execute(
                    """INSERT INTO llm_traces
                       (id, feature, model_id, input_tokens, output_tokens,
                        cost_usd, latency_ms, rag_chunks_used, error)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, 0, FALSE)""",
                    (str(uuid.uuid4()), "description_rewrite", BEDROCK_MODEL,
                     inp, out, cost, latency_ms),
                )
                conn.commit()
                logger.info("  → réécrit en %d ms | $%.6f", latency_ms, cost)

            # Respecter le rate limit Bedrock (1 req/s suffit largement pour Haiku)
            time.sleep(0.3)

        except Exception as exc:
            errors += 1
            logger.error("  Erreur sur %s : %s", animal_id, exc)
            conn.rollback()

    logger.info(
        "\n=== Terminé : %d animaux | %d erreurs | tokens %d/%d | coût total $%.5f ===",
        len(animals), errors, total_input, total_output, total_cost,
    )
    conn.close()


if __name__ == "__main__":
    main()