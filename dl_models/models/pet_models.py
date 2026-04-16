# dl_models/models/pet_models.py

import torch
import torch.nn as nn
import torchvision.models as models


class PetModel(nn.Module):
    def __init__(self, num_colors=5):
        super().__init__()

        backbone = models.mobilenet_v2(weights="DEFAULT")

        # feature extractor
        self.features = backbone.features

        # 🔥 FREEZE backbone
        for param in self.features.parameters():
            param.requires_grad = False

        self.pool = nn.AdaptiveAvgPool2d(1)

        # embedding léger
        self.fc = nn.Sequential(
            nn.Linear(1280, 128),
            nn.ReLU(),
            nn.Dropout(0.3)
        )

        # heads
        self.type_head = nn.Linear(128, 2)
        self.color_head = nn.Linear(128, num_colors)

    def forward(self, x):
        with torch.no_grad():  # 🔥 accélère encore
            x = self.features(x)

        x = self.pool(x).view(x.size(0), -1)
        x = self.fc(x)

        return self.type_head(x), self.color_head(x)