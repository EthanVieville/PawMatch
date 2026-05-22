# dl_models/predict.py

import io
import requests
import torch
import torch.nn.functional as F
from PIL import Image
import torchvision.transforms as transforms

from dl_models.models.pet_models import PetModel
from dl_models.data_pipeline.pet_dataset import BREED_LABELS

# Chats : indices 0-11 | Chiens : indices 12-36
_CAT_BREED_INDICES = list(range(0, 12))
_DOG_BREED_INDICES = list(range(12, 37))

_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def load_model(model_path: str) -> PetModel:
    model = PetModel()
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()
    return model


def predict_from_url(model: PetModel, image_url: str) -> dict | None:
    """
    Retourne {"species": str, "breed": str, "confidence": float} ou None si l'image est inaccessible.
    La race est contrainte à l'espèce détectée (pas de race chien pour un chat).
    """
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
    except Exception:
        return None

    tensor = _TRANSFORM(image).unsqueeze(0)

    with torch.no_grad():
        type_logits, _, breed_logits = model(tensor)

    type_probs = F.softmax(type_logits, dim=1)[0]
    breed_probs = F.softmax(breed_logits, dim=1)[0]

    species_idx = type_probs.argmax().item()
    species = "chat" if species_idx == 0 else "chien"

    # Contraindre la recherche de race à l'espèce prédite
    allowed = _CAT_BREED_INDICES if species == "chat" else _DOG_BREED_INDICES
    allowed_probs = breed_probs[allowed]
    best_local = allowed_probs.argmax().item()
    breed_idx = allowed[best_local]

    confidence = breed_probs[breed_idx].item()
    breed = BREED_LABELS[breed_idx]

    return {
        "species": species,
        "breed": breed,
        "confidence": round(confidence, 4),
    }


def predict_from_file(model: PetModel, image_path: str) -> dict | None:
    """Même logique que predict_from_url mais depuis un fichier local."""
    try:
        image = Image.open(image_path).convert("RGB")
    except Exception:
        return None

    tensor = _TRANSFORM(image).unsqueeze(0)

    with torch.no_grad():
        type_logits, _, breed_logits = model(tensor)

    type_probs = F.softmax(type_logits, dim=1)[0]
    breed_probs = F.softmax(breed_logits, dim=1)[0]

    species_idx = type_probs.argmax().item()
    species = "chat" if species_idx == 0 else "chien"

    allowed = _CAT_BREED_INDICES if species == "chat" else _DOG_BREED_INDICES
    allowed_probs = breed_probs[allowed]
    best_local = allowed_probs.argmax().item()
    breed_idx = allowed[best_local]

    confidence = breed_probs[breed_idx].item()

    return {
        "species": species,
        "breed": BREED_LABELS[breed_idx],
        "confidence": round(confidence, 4),
    }