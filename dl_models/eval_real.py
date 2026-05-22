"""
Évalue le modèle de classification de race sur les vraies images de la BD.

Lance depuis la racine du projet :
    python -m dl_models.eval_real
    python -m dl_models.eval_real --limit 100
    python -m dl_models.eval_real --model dl_models/utils/out/pet_model_best.pth --out resultats.csv

Prérequis locaux :
    pip install psycopg2-binary tqdm requests Pillow

PostgreSQL doit être accessible (Docker exposé sur :5432 par défaut).
"""

import argparse
import csv
import io
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import requests
import torch
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image

from dl_models.models.pet_models import PetModel
from dl_models.data_pipeline.pet_dataset import BREED_LABELS

# ── Config ────────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://pawmatch:pawmatch@localhost:5432/pawmatch",
)
DEFAULT_MODEL = "dl_models/utils/out/pet_model_best.pth"

# ── Mapping noms de race courants → label Oxford ──────────────────────────────
# Seuls les noms qui matchent un des 37 labels Oxford sont utiles pour l'accuracy.
BREED_MAP: dict[str, str] = {
    # Chats
    "siamois": "Siamese",       "siamese": "Siamese",
    "persan": "Persian",        "persian": "Persian",
    "maine coon": "Maine Coon",
    "sacré de birmanie": "Birman", "birman": "Birman",
    "ragdoll": "Ragdoll",
    "bengale": "Bengal",        "bengal": "Bengal",
    "abyssin": "Abyssinian",    "abyssinian": "Abyssinian",
    "british shorthair": "British Shorthair",
    "british": "British Shorthair",
    "sphynx": "Sphynx",         "sphinx": "Sphynx",
    "bombay": "Bombay",
    "bleu russe": "Russian Blue", "russian blue": "Russian Blue",
    "egyptian mau": "Egyptian Mau",
    # Chiens
    "beagle": "Beagle",
    "boxer": "Boxer",
    "chihuahua": "Chihuahua",
    "carlin": "Pug",            "pug": "Pug",
    "pomeranian": "Pomeranian", "spitz nain": "Pomeranian",
    "yorkshire terrier": "Yorkshire Terrier",
    "yorkshire": "Yorkshire Terrier",
    "staffordshire bull terrier": "Staffordshire Bull Terrier",
    "staffordshire": "Staffordshire Bull Terrier",
    "american bulldog": "American Bulldog",
    "basset hound": "Basset Hound", "basset": "Basset Hound",
    "samoyed": "Samoyed",       "samoyède": "Samoyed",
    "saint bernard": "Saint Bernard",
    "shiba inu": "Shiba Inu",   "shiba": "Shiba Inu",
    "miniature pinscher": "Miniature Pinscher",
    "pinscher nain": "Miniature Pinscher",
    "leonberger": "Leonberger",
    "newfoundland": "Newfoundland", "terre-neuve": "Newfoundland",
    "great pyrenees": "Great Pyrenees",
    "montagne des pyrénées": "Great Pyrenees",
    "keeshond": "Keeshond",
    "havanese": "Havanese",     "bichon havanais": "Havanese",
    "japanese chin": "Japanese Chin",
    "german shorthaired": "German Shorthaired",
    "braque allemand": "German Shorthaired",
    "wheaten terrier": "Wheaten Terrier",
    "scottish terrier": "Scottish Terrier",
    "scottish": "Scottish Terrier",
    "english cocker spaniel": "English Cocker Spaniel",
    "cocker": "English Cocker Spaniel",
    "english setter": "English Setter",
    "american pit bull terrier": "American Pit Bull Terrier",
    "pit bull": "American Pit Bull Terrier",
    "pitbull": "American Pit Bull Terrier",
}

_CAT_INDICES = list(range(0, 12))
_DOG_INDICES = list(range(12, 37))

_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PawMatch-eval/1.0)"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def map_race(race: str | None) -> str | None:
    """Convertit un nom de race libre vers un label Oxford, ou None."""
    if not race:
        return None
    s = race.lower().strip()
    if s in BREED_MAP:
        return BREED_MAP[s]
    for key, val in BREED_MAP.items():
        if key in s:
            return val
    return None


def fetch_image(url: str, timeout: int = 12) -> Image.Image | None:
    try:
        r = requests.get(url, timeout=timeout, headers=_HTTP_HEADERS)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return None


def infer(model: PetModel, image: Image.Image) -> dict:
    tensor = _TRANSFORM(image).unsqueeze(0)
    with torch.no_grad():
        type_logits, _, breed_logits = model(tensor)
    type_probs  = F.softmax(type_logits,  dim=1)[0]
    breed_probs = F.softmax(breed_logits, dim=1)[0]

    species_idx = type_probs.argmax().item()
    species     = "chat" if species_idx == 0 else "chien"

    allowed    = _CAT_INDICES if species == "chat" else _DOG_INDICES
    best_local = breed_probs[allowed].argmax().item()
    breed_idx  = allowed[best_local]

    return {
        "species":          species,
        "breed":            BREED_LABELS[breed_idx],
        "confidence":       round(breed_probs[breed_idx].item(), 4),
        "type_confidence":  round(type_probs.max().item(), 4),
    }


def fetch_animals(limit: int) -> list[dict]:
    try:
        import psycopg2
    except ImportError:
        sys.exit(
            "psycopg2 manquant.\n"
            "Installe-le avec : pip install psycopg2-binary"
        )

    m = re.match(
        r"postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)",
        DATABASE_URL,
    )
    if not m:
        sys.exit(f"DATABASE_URL invalide : {DATABASE_URL}")

    conn = psycopg2.connect(
        user=m.group(1), password=m.group(2),
        host=m.group(3), port=int(m.group(4) or 5432),
        dbname=m.group(5),
    )
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    a.id::text,
                    a.name,
                    a.species,
                    a.race,
                    (SELECT ai.url
                     FROM   animal_images ai
                     WHERE  ai.animal_id = a.id
                     ORDER  BY ai.position
                     LIMIT  1) AS img_url
                FROM   animals a
                WHERE  a.species IN ('chat', 'chien')
                  AND  a.source  != 'user'
                  AND  EXISTS (
                           SELECT 1 FROM animal_images ai
                           WHERE ai.animal_id = a.id
                       )
                ORDER BY (a.race IS NOT NULL) DESC, a.scraped_at DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "id":      r[0],
            "name":    r[1],
            "species": r[2],
            "race":    r[3],
            "img_url": r[4],
        }
        for r in rows
    ]


# ── Rapport terminal ──────────────────────────────────────────────────────────

def print_report(results: list[dict], n_total: int) -> None:
    ok  = [r for r in results if r["status"] == "ok"]
    sep = "=" * 58

    print(f"\n{sep}")
    print("RAPPORT D'ÉVALUATION — IMAGES RÉELLES")
    print(sep)
    print(f"Animaux tentés   : {n_total}")
    print(f"Images chargées  : {len(ok)}  ({100*len(ok)//max(n_total,1)}%)")
    fail = n_total - len(ok)
    print(f"Échecs (URL/net) : {fail}  ({100*fail//max(n_total,1)}%)")

    if not ok:
        print("\nAucun résultat disponible.")
        return

    # ── Espèce ────────────────────────────────────────────────────────────────
    sp_eval = [r for r in ok if r["species"]]
    if sp_eval:
        sp_ok = sum(r["pred_species"] == r["species"] for r in sp_eval)
        print(f"\nESPÈCE (chat / chien)")
        print(f"  Précision globale : {sp_ok}/{len(sp_eval)}  ({100*sp_ok//len(sp_eval)}%)")
        for sp in ("chat", "chien"):
            sub = [r for r in sp_eval if r["species"] == sp]
            if sub:
                ok_sp = sum(r["pred_species"] == sp for r in sub)
                print(f"  {sp.capitalize():8s} : {ok_sp}/{len(sub)}  ({100*ok_sp//len(sub)}%)")

    # ── Race (animaux mappables) ───────────────────────────────────────────────
    br_eval = [r for r in ok if r["oxford_expected"]]
    if br_eval:
        br_ok = sum(r["pred_breed"] == r["oxford_expected"] for r in br_eval)
        print(f"\nRACE (sur {len(br_eval)} animaux avec race mappable Oxford)")
        print(f"  Précision globale : {br_ok}/{len(br_eval)}  ({100*br_ok//len(br_eval)}%)")

        by_breed: dict[str, list[bool]] = defaultdict(list)
        for r in br_eval:
            by_breed[r["oxford_expected"]].append(
                r["pred_breed"] == r["oxford_expected"]
            )

        print("\n  Détail par race :")
        header = f"  {'Race attendue':<36} Exact   Prédit le plus souvent"
        print(header)
        print("  " + "-" * (len(header) - 2))

        for breed, vals in sorted(by_breed.items(), key=lambda x: -len(x[1])):
            ok_b = sum(vals)
            preds_for_breed = [
                r["pred_breed"]
                for r in br_eval
                if r["oxford_expected"] == breed
            ]
            most_common = Counter(preds_for_breed).most_common(1)[0][0]
            exact_str = f"{ok_b}/{len(vals)}"
            print(f"  {breed:<36} {exact_str:<7}  {most_common}")
    else:
        print("\nRACE : aucun animal dans la BD ne correspond aux 37 races Oxford.")
        print("  (Races vagues comme 'Européen' ou 'Labrador' ne sont pas dans le modèle)")
        print("\n  Top 10 races prédites par le modèle :")
        for breed, cnt in Counter(r["pred_breed"] for r in ok).most_common(10):
            print(f"    {breed:<35} {cnt}")

    # ── Distribution des scores de confiance ─────────────────────────────────
    confs = [r["confidence"] for r in ok if r["confidence"] is not None]
    if confs:
        avg = sum(confs) / len(confs)
        print(f"\nCONFIANCE MOYENNE : {avg:.1%}")
        print(f"  < 30%  : {sum(1 for c in confs if c < 0.30)}")
        print(f"  30–60% : {sum(1 for c in confs if 0.30 <= c < 0.60)}")
        print(f"  60–80% : {sum(1 for c in confs if 0.60 <= c < 0.80)}")
        print(f"  > 80%  : {sum(1 for c in confs if c >= 0.80)}")

    # ── Races DB les plus fréquentes sans mapping Oxford ─────────────────────
    no_map = [r for r in ok if r["race"] and not r["oxford_expected"]]
    if no_map:
        top = Counter(r["race"] for r in no_map).most_common(10)
        print(f"\nRACES DB SANS MAPPING OXFORD (non évaluables, top 10) :")
        for race, cnt in top:
            most_pred = Counter(
                r["pred_breed"] for r in no_map if r["race"] == race
            ).most_common(1)[0][0]
            print(f"  {race:<30} {cnt:>3}× → prédit : {most_pred}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Évaluation réelle du modèle de classification de race"
    )
    parser.add_argument("--limit",  type=int, default=150,
                        help="Nombre max d'animaux (défaut : 150)")
    parser.add_argument("--model",  type=str, default=DEFAULT_MODEL,
                        help="Chemin vers le fichier .pth")
    parser.add_argument("--out",    type=str,
                        default="dl_models/utils/eval_real_results.csv",
                        help="Fichier CSV de sortie")
    args = parser.parse_args()

    print("=== Évaluation sur images réelles de la BD ===\n")

    if not Path(args.model).exists():
        sys.exit(f"Modèle introuvable : {args.model}\n"
                 f"Lance d'abord l'entraînement ou ajuste --model.")

    print(f"Chargement du modèle : {args.model}")
    model = PetModel()
    model.load_state_dict(torch.load(args.model, map_location="cpu"))
    model.eval()
    print("Modèle chargé.\n")

    print(f"Récupération de {args.limit} animaux depuis la BD ({DATABASE_URL})...")
    try:
        animals = fetch_animals(args.limit)
    except SystemExit:
        raise
    except Exception as e:
        sys.exit(f"Erreur de connexion BD : {e}")

    print(f"{len(animals)} animaux récupérés "
          f"(dont {sum(1 for a in animals if a['race']) } avec race renseignée).\n")

    # ── Itération ────────────────────────────────────────────────────────────
    try:
        from tqdm import tqdm
        it = tqdm(animals, desc="Inférence", unit="img")
    except ImportError:
        it = animals

    results: list[dict] = []
    for animal in it:
        url = animal["img_url"]
        if not url or url.startswith("data:"):
            results.append({**animal, "status": "skip",
                            "pred_species": None, "pred_breed": None,
                            "confidence": None, "oxford_expected": None})
            continue

        img = fetch_image(url)
        if img is None:
            results.append({**animal, "status": "fetch_error",
                            "pred_species": None, "pred_breed": None,
                            "confidence": None, "oxford_expected": None})
            continue

        pred = infer(model, img)
        results.append({
            **animal,
            "status":          "ok",
            "pred_species":    pred["species"],
            "pred_breed":      pred["breed"],
            "confidence":      pred["confidence"],
            "oxford_expected": map_race(animal["race"]),
        })

    # ── Sauvegarde CSV ────────────────────────────────────────────────────────
    fields = [
        "id", "name", "species", "race", "img_url",
        "status", "pred_species", "pred_breed", "confidence", "oxford_expected",
    ]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in fields})

    # ── Rapport ───────────────────────────────────────────────────────────────
    n_ok = sum(1 for r in results if r["status"] == "ok")
    print_report(results, len(animals))
    print(f"\nCSV complet enregistré : {out_path.resolve()}")
    print("=" * 58 + "\n")


if __name__ == "__main__":
    main()