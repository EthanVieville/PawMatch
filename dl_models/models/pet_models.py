# dl_models/models/pet_models.py

import torch
import torch.nn as nn
import torchvision.models as models


class PetModel(nn.Module):
    def __init__(self, num_colors=5):
        super().__init__()

        # backbone pré-entraîné
        backbone = models.efficientnet_b0(pretrained=True)

        self.features = backbone.features
        self.pool = nn.AdaptiveAvgPool2d(1)

        # embedding commun
        self.fc = nn.Linear(1280, 256)
        self.relu = nn.ReLU()

        # 🔥 heads
        self.type_head = nn.Linear(256, 2)       # chat / chien
        self.color_head = nn.Linear(256, num_colors)

    def forward(self, x):
        x = self.features(x)
        x = self.pool(x).view(x.size(0), -1)

        x = self.relu(self.fc(x))

        type_out = self.type_head(x)
        color_out = self.color_head(x)

        return type_out, color_out