# dl_models/models/pet_models.py

import torch.nn as nn
import torchvision.models as models


class PetModel(nn.Module):
    def __init__(self, num_colors=5, num_breeds=37):
        super().__init__()

        backbone = models.mobilenet_v2(weights="DEFAULT")
        self.features = backbone.features

        # Geler tout le backbone
        for param in self.features.parameters():
            param.requires_grad = False

        # Dégeler les 3 derniers blocs pour la reconnaissance fine-grained
        for block in self.features[16:]:
            for param in block.parameters():
                param.requires_grad = True

        self.pool = nn.AdaptiveAvgPool2d(1)

        # Embedding plus large pour supporter la tête breed
        self.fc = nn.Sequential(
            nn.Linear(1280, 256),
            nn.ReLU(),
            nn.Dropout(0.3)
        )

        self.type_head = nn.Linear(256, 2)
        self.color_head = nn.Linear(256, num_colors)
        self.breed_head = nn.Linear(256, num_breeds)

    def forward(self, x):
        # Pas de no_grad : les derniers blocs sont entraînables
        x = self.features(x)
        x = self.pool(x).view(x.size(0), -1)
        x = self.fc(x)

        return self.type_head(x), self.color_head(x), self.breed_head(x)