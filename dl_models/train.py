import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from dl_models.data_pipeline.pet_dataset import PetDataset
from dl_models.models.pet_models import PetModel
from dl_models.utils.paths import PET_IMAGES_DIR, PET_TRAIN_FILE

# dataset
dataset = PetDataset(PET_IMAGES_DIR, PET_TRAIN_FILE)

dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

# model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = PetModel().to(device)

# loss
type_loss_fn = nn.CrossEntropyLoss()
color_loss_fn = nn.CrossEntropyLoss()

# optimizer
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

# training
for epoch in range(5):
    total_loss = 0

    for images, types, colors in dataloader:
        images = images.to(device)
        types = types.to(device)
        colors = colors.to(device)

        pred_type, pred_color = model(images)

        loss_type = type_loss_fn(pred_type, types)
        loss_color = color_loss_fn(pred_color, colors)

        loss = loss_type + loss_color

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch} | Loss: {total_loss:.4f}")