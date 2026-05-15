import json
import logging
import os
from typing import Generator, Optional

from sqlalchemy.orm import Session

from database import Animal, KnowledgeChunk

logger = logging.getLogger(__name__)

BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "eu.anthropic.claude-haiku-4-5-20251001-v1:0")

# ── Embedding encoder (lazy singleton) ───────────────────────────────────────

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer
        _encoder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _encoder


# ── Tool definitions (Bedrock tool use format) ────────────────────────────────

TOOLS = [
    {
        "name": "search_animals",
        "description": (
            "Cherche des animaux à adopter par similarité sémantique avec la description souhaitée. "
            "Utilise cet outil quand l'utilisateur cherche un animal, veut des recommandations, "
            "ou décrit le type d'animal qu'il souhaite adopter."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Description de l'animal recherché (caractère, taille, mode de vie, âge, etc.)",
                },
                "species": {
                    "type": "string",
                    "enum": ["chien", "chat", "lapin"],
                    "description": "Espèce souhaitée (optionnel)",
                },
                "max_age": {
                    "type": "integer",
                    "description": "Âge maximum en années (optionnel)",
                },
                "sex": {
                    "type": "string",
                    "enum": ["male", "femelle"],
                    "description": "Sexe souhaité (optionnel)",
                },
                "incompatibilities_to_avoid": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Liste des incompatibilités à exclure. "
                        "Exemples : ['enfants'] si l'utilisateur a des enfants, "
                        "['chiens'] s'il a déjà un chien, ['chats'] s'il a déjà un chat. "
                        "Retourne uniquement des animaux COMPATIBLES avec ces éléments."
                    ),
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_knowledge",
        "description": (
            "Cherche des informations sur les démarches d'adoption, les soins, ou les refuges. "
            "Utilise cet outil pour répondre aux questions sur les processus d'adoption, "
            "les documents requis, les frais, les conseils de soins par espèce."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Question ou thème à rechercher",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_animal",
        "description": "Récupère les détails complets d'un animal spécifique par son ID PawMatch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "animal_id": {
                    "type": "string",
                    "description": "L'ID PawMatch de l'animal (UUID)",
                }
            },
            "required": ["animal_id"],
        },
    },
    {
        "name": "search_animal_by_name",
        "description": (
            "Cherche un animal par son nom. Utilise cet outil quand l'utilisateur mentionne "
            "le nom d'un animal précis (ex: 'parle-moi de Luna', 'c'est quoi l'histoire de Rex')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Le nom de l'animal à rechercher",
                }
            },
            "required": ["name"],
        },
    },
]

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "Tu es PawBuddy, l'assistant bienveillant de PawMatch, une plateforme d'adoption animale française.\n\n"
    "Tu aides les utilisateurs à :\n"
    "- Trouver l'animal idéal parmi les animaux disponibles dans les refuges partenaires\n"
    "- Comprendre les démarches et modalités d'adoption\n"
    "- Obtenir des conseils de soins adaptés à leur situation\n\n"
    "Règles :\n"
    "- Utilise toujours les outils disponibles pour chercher des informations précises avant de répondre.\n"
    "- Pour chaque animal mentionné, crée un lien cliquable : [Nom de l'animal](/animals/ID_PAWMATCH)\n"
    "  L'ID PawMatch de chaque animal est indiqué dans les résultats de l'outil.\n"
    "- Mentionne toujours le refuge concerné.\n"
    "- Réponds toujours en français, de manière chaleureuse et bienveillante.\n"
    "- Pour les questions de santé, rappelle de consulter un vétérinaire.\n"
    "- Si une question est hors sujet, redirige poliment vers les thèmes de l'adoption animale."
)

# ── Tool implementations ──────────────────────────────────────────────────────

_SPECIES_KEYWORDS = {
    "chien": "chien", "chiot": "chien", "toutou": "chien", "chiens": "chien",
    "chat": "chat", "chaton": "chat", "chats": "chat",
    "lapin": "lapin", "lapins": "lapin",
}


def _format_animal(animal: Animal) -> str:
    lines = [
        f"Nom : {animal.name}",
        f"ID PawMatch : {animal.id}",
        f"Espèce : {animal.species or 'N/A'} | Race : {animal.race or 'N/A'}",
        f"Âge : {f'{animal.age} ans' if animal.age else 'N/A'} | Sexe : {animal.sex or 'N/A'}",
        f"Refuge : {animal.refuge or 'N/A'} (source : {animal.source})",
    ]
    if animal.description:
        lines.append(f"Description : {animal.description[:500]}")
    if animal.incompatibilities:
        lines.append(f"Incompatibilités : {', '.join(animal.incompatibilities)}")
    return "\n".join(lines)


def _tool_search_animals(
    query: str,
    species: Optional[str] = None,
    max_age: Optional[int] = None,
    sex: Optional[str] = None,
    incompatibilities_to_avoid: Optional[list] = None,
    db: Session = None,
) -> str:
    embedding = _get_encoder().encode(query).tolist()

    q = db.query(Animal).filter(Animal.embedding.isnot(None))

    if species:
        q = q.filter(Animal.species == species)
    else:
        msg = query.lower()
        detected = next((s for k, s in _SPECIES_KEYWORDS.items() if k in msg), None)
        if detected:
            q = q.filter(Animal.species == detected)

    if max_age is not None:
        q = q.filter(Animal.age <= max_age)

    if sex:
        q = q.filter(Animal.sex == sex)

    animals = q.order_by(Animal.embedding.cosine_distance(embedding)).limit(20).all()

    # Filter out animals incompatible with the user's household
    if incompatibilities_to_avoid and animals:
        avoid = {i.lower() for i in incompatibilities_to_avoid}
        animals = [
            a for a in animals
            if not (a.incompatibilities and avoid.intersection(i.lower() for i in a.incompatibilities))
        ]

    animals = animals[:6]

    if not animals:
        return "Aucun animal trouvé correspondant à ces critères."

    blocks = [f"[{i + 1}]\n{_format_animal(a)}" for i, a in enumerate(animals)]
    return "ANIMAUX DISPONIBLES :\n\n" + "\n\n".join(blocks)


def _tool_search_knowledge(query: str, db: Session = None) -> str:
    embedding = _get_encoder().encode(query).tolist()

    chunks = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.embedding.isnot(None))
        .order_by(KnowledgeChunk.embedding.cosine_distance(embedding))
        .limit(4)
        .all()
    )

    if not chunks:
        return "Aucune information disponible sur ce sujet."

    parts = [f"### {c.title}\n{c.content}" for c in chunks]
    return "INFORMATIONS DE RÉFÉRENCE :\n\n" + "\n\n".join(parts)


def _tool_get_animal(animal_id: str, db: Session = None) -> str:
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        return f"Animal avec l'ID {animal_id} introuvable."
    return _format_animal(animal)


def _tool_search_animal_by_name(name: str, db: Session = None) -> str:
    animals = db.query(Animal).filter(Animal.name.ilike(f"%{name}%")).limit(5).all()
    if not animals:
        return f"Aucun animal nommé '{name}' trouvé en base."
    blocks = [f"[{i + 1}]\n{_format_animal(a)}" for i, a in enumerate(animals)]
    return "ANIMAUX TROUVÉS :\n\n" + "\n\n".join(blocks)


def _execute_tool(name: str, inputs: dict, db: Session) -> str:
    if name == "search_animals":
        return _tool_search_animals(db=db, **inputs)
    if name == "search_knowledge":
        return _tool_search_knowledge(db=db, **inputs)
    if name == "get_animal":
        return _tool_get_animal(db=db, **inputs)
    if name == "search_animal_by_name":
        return _tool_search_animal_by_name(db=db, **inputs)
    return f"Outil inconnu : {name}"


# ── Agentic streaming ─────────────────────────────────────────────────────────

def stream_chat(
    message: str,
    history: list[dict],
    animal_id: Optional[str],
    db: Session,
    bedrock_client,
) -> Generator[str, None, None]:

    messages = list(history[-6:])

    # Inject animal page context into the user message
    if animal_id:
        animal = db.query(Animal).filter(Animal.id == animal_id).first()
        prefix = f"[L'utilisateur consulte la fiche de {animal.name} (ID PawMatch : {animal_id})]\n\n" if animal else ""
        messages.append({"role": "user", "content": prefix + message})
    else:
        messages.append({"role": "user", "content": message})

    try:
        # ── Step 1 : tool resolution (non-streaming) ──────────────────────────
        resp = bedrock_client.invoke_model(
            modelId=BEDROCK_MODEL,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "system": SYSTEM_PROMPT,
                "messages": messages,
                "tools": TOOLS,
                "max_tokens": 1024,
                "temperature": 0.7,
            }),
        )
        result = json.loads(resp["body"].read())

        if result.get("stop_reason") == "tool_use":
            tool_uses = [b for b in result["content"] if b["type"] == "tool_use"]

            # Append Claude's tool_use blocks to messages
            messages.append({"role": "assistant", "content": result["content"]})

            # Execute all requested tools
            tool_results = [
                {
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": _execute_tool(tu["name"], tu["input"], db),
                }
                for tu in tool_uses
            ]
            messages.append({"role": "user", "content": tool_results})

            # ── Step 2 : final streaming response ─────────────────────────────
            stream_resp = bedrock_client.invoke_model_with_response_stream(
                modelId=BEDROCK_MODEL,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "system": SYSTEM_PROMPT,
                    "messages": messages,
                    "tools": TOOLS,
                    "max_tokens": 1024,
                    "temperature": 0.7,
                }),
            )
            for event in stream_resp["body"]:
                chunk = json.loads(event["chunk"]["bytes"])
                if chunk.get("type") == "content_block_delta":
                    token = chunk["delta"].get("text", "")
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"

        else:
            # Claude answered directly without tools
            text = "".join(b.get("text", "") for b in result["content"] if b["type"] == "text")
            if text:
                yield f"data: {json.dumps({'token': text})}\n\n"

    except Exception as e:
        logger.error("Chat error: %s", e)
        yield f"data: {json.dumps({'token': 'Désolé, une erreur est survenue. Veuillez réessayer.'})}\n\n"

    yield "data: [DONE]\n\n"
