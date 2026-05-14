import json
import logging
import os
from typing import Generator, Optional

from sqlalchemy.orm import Session

from database import Animal, KnowledgeChunk

logger = logging.getLogger(__name__)

BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "eu.anthropic.claude-haiku-4-5-20251001-v1:0")

# ── Intent classification ─────────────────────────────────────────────────────

_INTENT_SYSTEM = """Tu es un classificateur d'intentions pour PawMatch, une plateforme d'adoption animale.
Analyse le message et réponds UNIQUEMENT par un de ces mots :
- find_animal : chercher un animal, recommandations, quel animal adopter
- adoption_process : démarches, documents, frais, visites, modalités d'adoption
- care_advice : soins, alimentation, santé, comportement, bien-être animal
- general : autre

Un seul mot, sans ponctuation ni explication."""

_INTENT_KEYWORDS = {
    "adoption_process": ["adopter", "adoption", "dossier", "document", "frais", "démarche", "procédure", "visite", "pré-visite", "modalité", "contrat"],
    "care_advice": ["soin", "nourrir", "alimentation", "vaccin", "santé", "comportement", "vétérinaire", "litière", "promenade", "habituer"],
}


def _classify_intent_keywords(message: str) -> str:
    msg = message.lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(k in msg for k in keywords):
            return intent
    return "find_animal"


def classify_intent(message: str, bedrock_client) -> str:
    try:
        resp = bedrock_client.invoke_model(
            modelId=BEDROCK_MODEL,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "system": _INTENT_SYSTEM,
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 10,
                "temperature": 0,
            }),
        )
        result = json.loads(resp["body"].read())["content"][0]["text"].strip().lower()
        valid = {"find_animal", "adoption_process", "care_advice", "general"}
        return result if result in valid else _classify_intent_keywords(message)
    except Exception as e:
        logger.warning("Intent classification via Bedrock failed, falling back to keywords: %s", e)
        return _classify_intent_keywords(message)


# ── System prompts ────────────────────────────────────────────────────────────

SYSTEM_PROMPTS = {
    "find_animal": (
        "Tu es PawBuddy, l'assistant bienveillant de PawMatch, une plateforme d'adoption animale française.\n"
        "Tu aides les utilisateurs à trouver l'animal idéal parmi les animaux disponibles dans les refuges partenaires.\n\n"
        "Règles :\n"
        "- Utilise UNIQUEMENT les animaux fournis dans le contexte. Ne mentionne jamais d'animaux absents.\n"
        "- Présente les animaux de manière chaleureuse en mettant en avant leurs points forts.\n"
        "- Pour chaque animal mentionné, crée un lien cliquable avec le format markdown : [Nom de l'animal](/animals/ID_PAWMATCH)\n"
        "  L'ID PawMatch de chaque animal est indiqué dans le contexte sous 'ID PawMatch'.\n"
        "- Mentionne toujours le refuge concerné.\n"
        "- Si aucun animal ne correspond parfaitement, propose les plus proches en expliquant pourquoi.\n"
        "- Réponds toujours en français."
    ),
    "adoption_process": (
        "Tu es PawBuddy, l'assistant bienveillant de PawMatch, une plateforme d'adoption animale française.\n"
        "Tu aides les utilisateurs à comprendre et naviguer le processus d'adoption.\n\n"
        "Règles :\n"
        "- Utilise UNIQUEMENT les informations fournies dans le contexte. Ne fabrique jamais d'informations.\n"
        "- Si la question porte sur un animal spécifique, utilise ses informations (refuge, incompatibilités, description).\n"
        "- Sois clair sur les documents requis, les étapes et les frais.\n"
        "- Oriente vers le refuge pour les questions très spécifiques.\n"
        "- Réponds toujours en français, de manière claire et rassurante."
    ),
    "care_advice": (
        "Tu es PawBuddy, l'assistant bienveillant de PawMatch, une plateforme d'adoption animale française.\n"
        "Tu donnes des conseils pratiques pour prendre soin des animaux adoptés.\n\n"
        "Règles :\n"
        "- Utilise UNIQUEMENT les informations fournies dans le contexte.\n"
        "- Sois concret et pratique dans tes conseils.\n"
        "- Adapte tes conseils à l'espèce et la situation mentionnées.\n"
        "- Rappelle toujours qu'un vétérinaire est la référence pour les questions de santé.\n"
        "- Réponds toujours en français, de manière bienveillante."
    ),
    "general": (
        "Tu es PawBuddy, l'assistant bienveillant de PawMatch, une plateforme d'adoption animale française.\n"
        "Tu réponds aux questions générales sur l'adoption animale et la plateforme.\n\n"
        "Règles :\n"
        "- Utilise UNIQUEMENT les informations fournies dans le contexte.\n"
        "- Pour les questions hors sujet, redirige poliment vers les thèmes de l'adoption animale.\n"
        "- Réponds toujours en français."
    ),
}


# ── RAG context building ──────────────────────────────────────────────────────

_SPECIES_KEYWORDS = {
    "chien": "chien", "chiot": "chien", "toutou": "chien", "chiens": "chien",
    "chat": "chat", "chaton": "chat", "chats": "chat",
    "lapin": "lapin", "lapins": "lapin",
}

_CATEGORY_MAP = {
    "adoption_process": ["adoption_process", "shelter_info"],
    "care_advice": ["care_advice"],
    "general": ["adoption_process", "shelter_info", "care_advice"],
    "find_animal": [],
}


def _format_animal(animal: Animal) -> str:
    lines = [
        f"Nom : {animal.name}",
        f"ID PawMatch : {animal.id}",
        f"Espèce : {animal.species or 'N/A'} | Race : {animal.race or 'N/A'}",
        f"Âge : {f'{animal.age} ans' if animal.age else 'N/A'} | Sexe : {animal.sex or 'N/A'}",
        f"Refuge : {animal.refuge or 'N/A'} (source : {animal.source})",
        f"Lien fiche originale : {animal.source_url}",
    ]
    if animal.description:
        lines.append(f"Description : {animal.description[:500]}")
    if animal.incompatibilities:
        lines.append(f"Incompatibilités : {', '.join(animal.incompatibilities)}")
    return "\n".join(lines)


def _search_animals(message: str, db: Session, limit: int = 5) -> list[Animal]:
    msg = message.lower()
    detected_species = next((s for k, s in _SPECIES_KEYWORDS.items() if k in msg), None)

    query = db.query(Animal)
    if detected_species:
        query = query.filter(Animal.species == detected_species)

    animals = query.limit(limit).all()
    if not animals:
        animals = db.query(Animal).limit(limit).all()
    return animals


def _build_context(intent: str, message: str, animal_id: Optional[str], db: Session) -> str:
    sections = []

    # Specific animal context (when user is on an animal's page)
    if animal_id:
        animal = db.query(Animal).filter(Animal.id == animal_id).first()
        if animal:
            sections.append("ANIMAL CONCERNÉ :\n" + _format_animal(animal))

    # Animal search results
    if intent == "find_animal":
        animals = _search_animals(message, db)
        if animals:
            blocks = [f"[{i + 1}]\n{_format_animal(a)}" for i, a in enumerate(animals)]
            sections.append("ANIMAUX DISPONIBLES :\n\n" + "\n\n".join(blocks))

    # Knowledge chunks (adoption process, care advice)
    categories = _CATEGORY_MAP.get(intent, [])
    if categories:
        chunks = db.query(KnowledgeChunk).filter(KnowledgeChunk.category.in_(categories)).all()
        if chunks:
            parts = [f"### {c.title}\n{c.content}" for c in chunks]
            sections.append("INFORMATIONS DE RÉFÉRENCE :\n\n" + "\n\n".join(parts))

    return "\n\n---\n\n".join(sections) if sections else "Aucun contexte disponible."


# ── Streaming ─────────────────────────────────────────────────────────────────

def stream_chat(
    message: str,
    history: list[dict],
    animal_id: Optional[str],
    db: Session,
    bedrock_client,
) -> Generator[str, None, None]:
    intent = classify_intent(message, bedrock_client)
    context = _build_context(intent, message, animal_id, db)
    system = f"{SYSTEM_PROMPTS[intent]}\n\n---\nCONTEXTE :\n{context}"

    messages = history[-6:] + [{"role": "user", "content": message}]

    try:
        response = bedrock_client.invoke_model_with_response_stream(
            modelId=BEDROCK_MODEL,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "system": system,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.7,
            }),
        )
        for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            if chunk.get("type") == "content_block_delta":
                token = chunk["delta"].get("text", "")
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"

    except Exception as e:
        logger.error("Bedrock streaming error: %s", e)
        yield f"data: {json.dumps({'token': 'Désolé, une erreur est survenue. Veuillez réessayer.'})}\n\n"

    yield "data: [DONE]\n\n"
