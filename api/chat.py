import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Generator, Optional

from sqlalchemy.orm import Session

from database import Animal, KnowledgeChunk, LLMTrace, LLMCache

logger = logging.getLogger(__name__)

# ── Pricing ($ per 1M tokens) ─────────────────────────────────────────────────

_PRICING = {
    "haiku":  (0.80,  4.00),
    "sonnet": (3.00,  15.00),
    "opus":   (15.00, 75.00),
}


def _compute_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    tier = next((k for k in _PRICING if k in model_id.lower()), "haiku")
    inp, out = _PRICING[tier]
    return (input_tokens * inp + output_tokens * out) / 1_000_000


def _save_trace(
    db: Session,
    feature: str,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    tool_calls: list,
    rag_chunks_used: int,
    error: bool,
) -> None:
    try:
        trace = LLMTrace(
            feature=feature,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=_compute_cost(model_id, input_tokens, output_tokens),
            latency_ms=latency_ms,
            tool_calls=tool_calls or None,
            rag_chunks_used=rag_chunks_used,
            error=error,
        )
        db.add(trace)
        db.commit()
    except Exception as exc:
        logger.error("Failed to save LLM trace: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass

BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "eu.anthropic.claude-haiku-4-5-20251001-v1:0")

# ── Semantic cache ────────────────────────────────────────────────────────────

CACHE_SIMILARITY_THRESHOLD = 0.92   # cosine similarity; distance = 1 - threshold
CACHE_TTL_HOURS = 24


def _lookup_cache(message: str, db: Session) -> Optional[str]:
    try:
        embedding = _get_encoder().encode(message).tolist()
        threshold = 1 - CACHE_SIMILARITY_THRESHOLD
        entry = (
            db.query(LLMCache)
            .filter(LLMCache.expires_at > datetime.now(timezone.utc))
            .filter(LLMCache.query_embedding.cosine_distance(embedding) < threshold)
            .order_by(LLMCache.query_embedding.cosine_distance(embedding))
            .first()
        )
        if entry:
            entry.hit_count += 1
            entry.last_hit_at = datetime.now(timezone.utc)
            db.commit()
            return entry.response_text
    except Exception as exc:
        logger.error("Cache lookup error: %s", exc)
    return None


def _store_cache(message: str, response: str, db: Session) -> None:
    try:
        embedding = _get_encoder().encode(message).tolist()
        entry = LLMCache(
            query_text=message,
            query_embedding=embedding,
            response_text=response,
            feature="chat",
            hit_count=0,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=CACHE_TTL_HOURS),
        )
        db.add(entry)
        db.commit()
    except Exception as exc:
        logger.error("Cache store error: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass


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
    source: Optional[str] = None,
) -> Generator[str, None, None]:

    _t = {
        "start": time.time(),
        "input_tokens": 0,
        "output_tokens": 0,
        "tool_calls": [],
        "rag_chunks": 0,
        "error": False,
        "response_tokens": [],
        "cacheable": animal_id is None and source != "quiz",
        "cache_hit": False,
    }

    messages = list(history[-6:])

    # Inject animal page context into the user message
    if animal_id:
        animal = db.query(Animal).filter(Animal.id == animal_id).first()
        prefix = f"[L'utilisateur consulte la fiche de {animal.name} (ID PawMatch : {animal_id})]\n\n" if animal else ""
        messages.append({"role": "user", "content": prefix + message})
    else:
        messages.append({"role": "user", "content": message})

    # ── Semantic cache lookup (context-free queries only) ─────────────────────
    _cached_response: Optional[str] = None
    if _t["cacheable"]:
        _cached_response = _lookup_cache(message, db)
        if _cached_response:
            _t["cache_hit"] = True

    try:
        if _t["cache_hit"]:
            yield f"data: {json.dumps({'token': _cached_response})}\n\n"
        else:
            try:
                # ── Step 1 : tool resolution (non-streaming) ──────────────────────
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

                usage = result.get("usage", {})
                _t["input_tokens"] += usage.get("input_tokens", 0)
                _t["output_tokens"] += usage.get("output_tokens", 0)

                if result.get("stop_reason") == "tool_use":
                    tool_uses = [b for b in result["content"] if b["type"] == "tool_use"]

                    for tu in tool_uses:
                        _t["tool_calls"].append({"name": tu["name"], "input": tu["input"]})
                        if tu["name"] == "search_knowledge":
                            _t["rag_chunks"] += 4
                        elif tu["name"] == "search_animals":
                            _t["rag_chunks"] += 6

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

                    # ── Step 2 : final streaming response ─────────────────────────
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
                        chunk_type = chunk.get("type")
                        if chunk_type == "message_start":
                            u = chunk.get("message", {}).get("usage", {})
                            _t["input_tokens"] += u.get("input_tokens", 0)
                        elif chunk_type == "message_delta":
                            _t["output_tokens"] += chunk.get("usage", {}).get("output_tokens", 0)
                        elif chunk_type == "content_block_delta":
                            token = chunk["delta"].get("text", "")
                            if token:
                                _t["response_tokens"].append(token)
                                yield f"data: {json.dumps({'token': token})}\n\n"

                else:
                    # Claude answered directly without tools
                    direct_text = "".join(b.get("text", "") for b in result["content"] if b["type"] == "text")
                    if direct_text:
                        _t["response_tokens"].append(direct_text)
                        yield f"data: {json.dumps({'token': direct_text})}\n\n"

            except Exception as e:
                _t["error"] = True
                logger.error("Chat error: %s", e)
                yield f"data: {json.dumps({'token': 'Désolé, une erreur est survenue. Veuillez réessayer.'})}\n\n"

        yield "data: [DONE]\n\n"

    finally:
        # Toujours tracé, même si le client ferme la connexion SSE avant la fin
        _feature = source or "chat"
        if _t["cache_hit"]:
            _save_trace(
                db=db,
                feature=f"{_feature}_cached",
                model_id=BEDROCK_MODEL,
                input_tokens=0,
                output_tokens=0,
                latency_ms=int((time.time() - _t["start"]) * 1000),
                tool_calls=[],
                rag_chunks_used=0,
                error=False,
            )
        else:
            _save_trace(
                db=db,
                feature=_feature,
                model_id=BEDROCK_MODEL,
                input_tokens=_t["input_tokens"],
                output_tokens=_t["output_tokens"],
                latency_ms=int((time.time() - _t["start"]) * 1000),
                tool_calls=_t["tool_calls"],
                rag_chunks_used=_t["rag_chunks"],
                error=_t["error"],
            )
            if _t["cacheable"] and not _t["error"] and _t["response_tokens"]:
                _store_cache(message, "".join(_t["response_tokens"]), db)
