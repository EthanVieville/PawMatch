# dl_models/train.py

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torch.utils.tensorboard import SummaryWriter

from dl_models.data_pipeline.pet_dataset import PetDataset
from dl_models.models.pet_models import PetModel
from dl_models.utils.paths import (
    PET_IMAGES_DIR, 
    PET_TRAIN_FILE, 
    OUT_PET_MODELS
)

from dl_models.utils.tools_models import (
    train_one_epoch, 
    evaluate, 
    save_confusion_matrix, 
    save_model
)


def main():
    ### CONFIG ###
    # tensorboard
    writer = SummaryWriter("runs/pet_experiment")

    # dataset
    dataset = PetDataset(PET_IMAGES_DIR, PET_TRAIN_FILE)

    # SPLIT 
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size

    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    print("SPLIT DATASET OK\n")

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False, num_workers=4)

    # ======= TRAIN =======
    # model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)
    print("CUDA available:", torch.cuda.is_available())

    model = PetModel().to(device)

    # loss
    type_loss_fn = nn.CrossEntropyLoss()
    color_loss_fn = nn.CrossEntropyLoss()

    # optimizer
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    # training
    for epoch in range(5):
        print(f"\nEpoch {epoch}\n")

        train_metrics = train_one_epoch(
            model, train_loader, optimizer, type_loss_fn, color_loss_fn, device
        )

        print(f"TRAIN | Loss: {train_metrics['loss']:.4f} | Type acc: {train_metrics['type_acc']:.3f} | Color acc: {train_metrics['color_acc']:.3f}")

        writer.add_scalar("Loss/train", train_metrics["loss"], epoch)
        writer.add_scalar("Accuracy/type_train", train_metrics["type_acc"], epoch)
        writer.add_scalar("Accuracy/color_train", train_metrics["color_acc"], epoch)

        val_metrics = evaluate(
            model, val_loader, type_loss_fn, color_loss_fn, device
        )

        print(f"VAL | Loss: {val_metrics['loss']:.4f} | Type acc: {val_metrics['type_acc']:.3f} | Color acc: {val_metrics['color_acc']:.3f}")

        writer.add_scalar("Loss/val", val_metrics["loss"], epoch)
        writer.add_scalar("Accuracy/type_val", val_metrics["type_acc"], epoch)
        writer.add_scalar("Accuracy/color_val", val_metrics["color_acc"], epoch)

    save_model(model, f"{OUT_PET_MODELS}/pet_model_epoch_{epoch}_v1.pth")

    print("\nGenerating confusion matrices...")

    save_confusion_matrix(
        val_metrics["type_labels"],
        val_metrics["type_preds"],
        ["Chat", "Chien"],
        f"{OUT_PET_MODELS}/cm_type.png",
        "Confusion Matrix - Type"
    )

    save_confusion_matrix(
        val_metrics["color_labels"],
        val_metrics["color_preds"],
        ["Black", "White", "Brown", "Gray", "Other"],
        f"{OUT_PET_MODELS}/cm_color.png",
        "Confusion Matrix - Color"
    )


if __name__ == "__main__":
    main()