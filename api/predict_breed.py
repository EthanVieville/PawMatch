# api/predict_breed.py
# Module standalone pour la prédiction de race depuis une image.
# Transforms faites manuellement via PIL + numpy (pas besoin de torchvision.transforms).
# torchvision est quand même requis pour l'architecture MobileNetV2.

import base64
import io
import os
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

BREED_LABELS = [
    "Abyssinian", "Bengal", "Birman", "Bombay", "British Shorthair",
    "Egyptian Mau", "Maine Coon", "Persian", "Ragdoll", "Russian Blue",
    "Siamese", "Sphynx",
    "American Bulldog", "American Pit Bull Terrier", "Basset Hound",
    "Beagle", "Boxer", "Chihuahua", "English Cocker Spaniel", "English Setter",
    "German Shorthaired", "Great Pyrenees", "Havanese", "Japanese Chin",
    "Keeshond", "Leonberger", "Miniature Pinscher", "Newfoundland",
    "Pomeranian", "Pug", "Saint Bernard", "Samoyed", "Scottish Terrier",
    "Shiba Inu", "Staffordshire Bull Terrier", "Wheaten Terrier",
    "Yorkshire Terrier",
]

_CAT_INDICES = list(range(0, 12))
_DOG_INDICES = list(range(12, 37))

_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class _PetModel(nn.Module):
    """Reproduction exacte de PetModel pour le chargement des poids sans importer dl_models."""
    def __init__(self):
        super().__init__()
        import torchvision.models as tv
        backbone = tv.mobilenet_v2(weights=None)
        self.features = backbone.features
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(nn.Linear(1280, 256), nn.ReLU(), nn.Dropout(0.3))
        self.type_head  = nn.Linear(256, 2)
        self.color_head = nn.Linear(256, 5)
        self.breed_head = nn.Linear(256, 37)

    def forward(self, x):
        x = self.features(x)
        x = self.pool(x).view(x.size(0), -1)
        x = self.fc(x)
        return self.type_head(x), self.color_head(x), self.breed_head(x)


def _preprocess(image: Image.Image) -> torch.Tensor:
    image = image.resize((224, 224), Image.LANCZOS)
    arr = np.array(image).astype(np.float32) / 255.0
    arr = (arr - _IMAGENET_MEAN) / _IMAGENET_STD
    arr = arr.transpose(2, 0, 1)
    return torch.tensor(arr, dtype=torch.float32).unsqueeze(0)


def load_breed_model(model_path: str | None = None) -> "_PetModel | None":
    if model_path is None:
        model_path = os.getenv("BREED_MODEL_PATH", "models/pet_model_best.pth")
    if not Path(model_path).exists():
        return None
    try:
        model = _PetModel()
        model.load_state_dict(torch.load(model_path, map_location="cpu"))
        model.eval()
        return model
    except Exception:
        return None


def predict_from_bytes(model: "_PetModel", image_bytes: bytes) -> dict | None:
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return None
    return _run(model, image)


def predict_from_base64(model: "_PetModel", b64: str) -> dict | None:
    try:
        return predict_from_bytes(model, base64.b64decode(b64))
    except Exception:
        return None


def _run(model: "_PetModel", image: Image.Image) -> dict:
    tensor = _preprocess(image)
    with torch.no_grad():
        type_logits, _, breed_logits = model(tensor)

    type_probs  = F.softmax(type_logits,  dim=1)[0]
    breed_probs = F.softmax(breed_logits, dim=1)[0]

    species_idx = type_probs.argmax().item()
    species = "chat" if species_idx == 0 else "chien"

    allowed = _CAT_INDICES if species == "chat" else _DOG_INDICES
    best_local = breed_probs[allowed].argmax().item()
    breed_idx = allowed[best_local]

    return {
        "species": species,
        "breed": BREED_LABELS[breed_idx],
        "confidence": round(breed_probs[breed_idx].item(), 4),
    }