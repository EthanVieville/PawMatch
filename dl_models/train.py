# dl_models/train.py

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torch.utils.tensorboard import SummaryWriter

from dl_models.data_pipeline.pet_dataset import PetDataset, BREED_LABELS
from dl_models.models.pet_models import PetModel
from dl_models.utils.paths import PET_IMAGES_DIR, PET_TRAIN_FILE, OUT_PET_MODELS
from dl_models.utils.tools_models import (
    train_one_epoch,
    evaluate,
    log_sample_predictions,
    log_confusion_matrix_tb,
    log_per_class_f1,
    print_classification_report,
    save_confusion_matrix,
    save_model,
)

EPOCHS = 20
BATCH_SIZE = 32
LR = 1e-3
VIZ_EVERY = 5   # fréquence (en epochs) des visualisations lourdes


def main():
    writer = SummaryWriter("runs/pet_experiment")

    # Deux instances du dataset : augmentée pour train, brute pour val
    torch.manual_seed(42)
    _ref = PetDataset(PET_IMAGES_DIR, PET_TRAIN_FILE, augment=False)
    train_size = int(0.8 * len(_ref))
    val_size = len(_ref) - train_size

    train_ds = PetDataset(PET_IMAGES_DIR, PET_TRAIN_FILE, augment=True)
    val_ds = PetDataset(PET_IMAGES_DIR, PET_TRAIN_FILE, augment=False)

    torch.manual_seed(42)
    train_ds, _ = random_split(train_ds, [train_size, val_size])
    torch.manual_seed(42)
    _, val_ds = random_split(val_ds, [train_size, val_size])

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=4)

    print(f"Dataset  — train : {train_size}  |  val : {val_size}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device   — {device}")
    if device.type == "cuda":
        print(f"GPU      — {torch.cuda.get_device_name(0)}\n")
    else:
        print()

    model = PetModel().to(device)

    type_loss_fn = nn.CrossEntropyLoss()
    color_loss_fn = nn.CrossEntropyLoss()
    breed_loss_fn = nn.CrossEntropyLoss()

    # LR différencié : backbone dégelé x10 plus lent que les têtes
    backbone_params = [p for p in model.features[16:].parameters() if p.requires_grad]
    head_params = (
        list(model.fc.parameters())
        + list(model.type_head.parameters())
        + list(model.color_head.parameters())
        + list(model.breed_head.parameters())
    )
    optimizer = torch.optim.Adam([
        {"params": backbone_params, "lr": LR * 0.1},
        {"params": head_params,     "lr": LR},
    ])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_breed_acc = 0.0
    val_m = None

    for epoch in range(EPOCHS):
        print(f"{'─' * 55}")
        print(f"Epoch {epoch + 1:>2}/{EPOCHS}  |  LR heads = {scheduler.get_last_lr()[-1]:.2e}")

        train_m = train_one_epoch(
            model, train_loader, optimizer,
            type_loss_fn, color_loss_fn, breed_loss_fn, device,
        )
        print(f"  TRAIN  loss={train_m['loss']:.4f}  type={train_m['type_acc']:.3f}  breed={train_m['breed_acc']:.3f}")

        val_m = evaluate(
            model, val_loader,
            type_loss_fn, color_loss_fn, breed_loss_fn, device,
        )
        print(f"  VAL    loss={val_m['loss']:.4f}  type={val_m['type_acc']:.3f}  breed={val_m['breed_acc']:.3f}")

        # ── Scalars TensorBoard ──────────────────────────────────────
        writer.add_scalars("Loss", {"train": train_m["loss"], "val": val_m["loss"]}, epoch)
        writer.add_scalars("Accuracy/type",  {"train": train_m["type_acc"],  "val": val_m["type_acc"]},  epoch)
        writer.add_scalars("Accuracy/breed", {"train": train_m["breed_acc"], "val": val_m["breed_acc"]}, epoch)
        writer.add_scalar("LR/heads",    scheduler.get_last_lr()[-1], epoch)
        writer.add_scalar("LR/backbone", scheduler.get_last_lr()[0],  epoch)

        scheduler.step()

        # ── Visualisations lourdes tous les VIZ_EVERY epochs ────────
        if (epoch + 1) % VIZ_EVERY == 0 or epoch == 0:
            log_sample_predictions(writer, model, val_loader, device, BREED_LABELS, epoch)
            log_per_class_f1(writer, val_m["breed_labels"], val_m["breed_preds"], BREED_LABELS, epoch)
            log_confusion_matrix_tb(writer, val_m["type_labels"], val_m["type_preds"], ["Chat", "Chien"], "type", epoch)

        # ── Sauvegarde du meilleur modèle ───────────────────────────
        if val_m["breed_acc"] > best_breed_acc:
            best_breed_acc = val_m["breed_acc"]
            save_model(model, f"{OUT_PET_MODELS}/pet_model_best.pth")
            print(f"  ★ Nouveau meilleur breed acc : {best_breed_acc:.3f}")

    # ── Fin d'entraînement : visualisations finales ──────────────────
    print(f"\n{'═' * 55}")
    print(f"Entraînement terminé  |  Meilleur breed acc : {best_breed_acc:.3f}")

    save_model(model, f"{OUT_PET_MODELS}/pet_model_final.pth")

    log_confusion_matrix_tb(writer, val_m["breed_labels"], val_m["breed_preds"], BREED_LABELS, "breed", EPOCHS - 1)
    log_per_class_f1(writer, val_m["breed_labels"], val_m["breed_preds"], BREED_LABELS, EPOCHS - 1)

    # Rapport texte dans le terminal
    print_classification_report(val_m["breed_labels"], val_m["breed_preds"], BREED_LABELS)

    # Matrices sauvegardées en fichier (en plus de TensorBoard)
    save_confusion_matrix(
        val_m["type_labels"], val_m["type_preds"],
        ["Chat", "Chien"],
        f"{OUT_PET_MODELS}/cm_type.png", "Confusion Matrix — Type",
    )
    save_confusion_matrix(
        val_m["breed_labels"], val_m["breed_preds"],
        BREED_LABELS,
        f"{OUT_PET_MODELS}/cm_breed.png", "Confusion Matrix — Breed",
    )

    writer.close()
    print(f"\nTensorBoard  →  tensorboard --logdir runs/pet_experiment")


if __name__ == "__main__":
    main()