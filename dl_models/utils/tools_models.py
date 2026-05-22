# dl_models/utils/tools_models.py

import os
import torch
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, classification_report

_UNNORM_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
_UNNORM_STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)


def _unnormalize(tensor: torch.Tensor) -> np.ndarray:
    img = (tensor.cpu() * _UNNORM_STD + _UNNORM_MEAN).clamp(0, 1)
    return img.permute(1, 2, 0).numpy()


# =========================
# TRAIN LOOP
# =========================
def train_one_epoch(model, loader, optimizer, type_loss_fn, color_loss_fn, breed_loss_fn, device):
    model.train()

    total_loss = 0
    correct_type = 0
    correct_breed = 0
    total = 0

    for images, types, colors, breeds in loader:
        images = images.to(device)
        types = types.to(device)
        colors = colors.to(device)
        breeds = breeds.to(device)

        pred_type, pred_color, pred_breed = model(images)

        loss = (
            type_loss_fn(pred_type, types)
            + 0.3 * color_loss_fn(pred_color, colors)
            + breed_loss_fn(pred_breed, breeds)
        )

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        correct_type += (pred_type.argmax(dim=1) == types).sum().item()
        correct_breed += (pred_breed.argmax(dim=1) == breeds).sum().item()
        total += types.size(0)

    return {
        "loss": total_loss / len(loader),
        "type_acc": correct_type / total,
        "breed_acc": correct_breed / total,
    }


# =========================
# VALIDATION LOOP
# =========================
def evaluate(model, loader, type_loss_fn, color_loss_fn, breed_loss_fn, device):
    model.eval()

    val_loss = 0
    correct_type = 0
    correct_breed = 0
    total = 0

    all_type_preds, all_type_labels = [], []
    all_breed_preds, all_breed_labels = [], []

    with torch.no_grad():
        for images, types, colors, breeds in loader:
            images = images.to(device)
            types = types.to(device)
            colors = colors.to(device)
            breeds = breeds.to(device)

            pred_type, pred_color, pred_breed = model(images)

            loss = (
                type_loss_fn(pred_type, types)
                + 0.3 * color_loss_fn(pred_color, colors)
                + breed_loss_fn(pred_breed, breeds)
            )
            val_loss += loss.item()

            pred_type_labels = pred_type.argmax(dim=1)
            pred_breed_labels = pred_breed.argmax(dim=1)

            correct_type += (pred_type_labels == types).sum().item()
            correct_breed += (pred_breed_labels == breeds).sum().item()
            total += types.size(0)

            all_type_preds.extend(pred_type_labels.cpu().numpy())
            all_type_labels.extend(types.cpu().numpy())
            all_breed_preds.extend(pred_breed_labels.cpu().numpy())
            all_breed_labels.extend(breeds.cpu().numpy())

    return {
        "loss": val_loss / len(loader),
        "type_acc": correct_type / total,
        "breed_acc": correct_breed / total,
        "type_preds": all_type_preds,
        "type_labels": all_type_labels,
        "breed_preds": all_breed_preds,
        "breed_labels": all_breed_labels,
    }


# =========================
# TENSORBOARD — GRILLE D'IMAGES
# =========================
def log_sample_predictions(writer, model, val_loader, device, breed_labels, epoch, n=16):
    """Log une grille d'images annotées (vrai vs prédit) dans TensorBoard."""
    model.eval()
    images_batch, _, _, breeds_batch = next(iter(val_loader))
    n = min(n, len(images_batch))
    images_batch = images_batch[:n].to(device)
    breeds_batch = breeds_batch[:n]

    with torch.no_grad():
        _, _, breed_logits = model(images_batch)

    pred_breeds = breed_logits.argmax(dim=1).cpu()

    cols = 4
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3.8))
    axes = axes.flatten()

    for i in range(n):
        img = _unnormalize(images_batch[i])
        true_label = breed_labels[breeds_batch[i].item()]
        pred_label = breed_labels[pred_breeds[i].item()]
        correct = pred_breeds[i].item() == breeds_batch[i].item()

        axes[i].imshow(img)
        axes[i].set_title(
            f"✓ {true_label}" if correct else f"Vrai : {true_label}\nPréd : {pred_label}",
            fontsize=7,
            color="#2ecc71" if correct else "#e74c3c",
            pad=3,
        )
        axes[i].axis("off")

    for i in range(n, len(axes)):
        axes[i].axis("off")

    plt.suptitle(f"Epoch {epoch + 1} — Prédictions sur validation", fontsize=9, y=1.01)
    plt.tight_layout()
    writer.add_figure("Predictions/grille", fig, epoch)
    plt.close(fig)


# =========================
# TENSORBOARD — MATRICE DE CONFUSION
# =========================
def log_confusion_matrix_tb(writer, labels, preds, class_names, tag, epoch):
    """Log une matrice de confusion normalisée dans TensorBoard."""
    cm = confusion_matrix(labels, preds, labels=range(len(class_names)))
    cm_norm = cm.astype(float) / (cm.sum(axis=1, keepdims=True) + 1e-8)

    fig_size = max(6, len(class_names) // 2)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size))
    im = ax.imshow(cm_norm, vmin=0, vmax=1, cmap="Blues")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax.set_xticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=90, fontsize=6)
    ax.set_yticks(range(len(class_names)))
    ax.set_yticklabels(class_names, fontsize=6)
    ax.set_xlabel("Prédit", fontsize=8)
    ax.set_ylabel("Vrai", fontsize=8)
    ax.set_title(f"Matrice de confusion — {tag} (epoch {epoch + 1})", fontsize=9)

    plt.tight_layout()
    writer.add_figure(f"ConfusionMatrix/{tag}", fig, epoch)
    plt.close(fig)


# =========================
# TENSORBOARD — F1 PAR RACE
# =========================
def log_per_class_f1(writer, labels, preds, class_names, epoch):
    """Log un bar chart F1 par race + mean F1/precision/recall scalars."""
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds,
        labels=range(len(class_names)),
        zero_division=0,
    )

    # Bar chart coloré par niveau de performance
    colors = ["#2ecc71" if v >= 0.7 else "#f39c12" if v >= 0.4 else "#e74c3c" for v in f1]
    fig, ax = plt.subplots(figsize=(max(14, len(class_names) // 2), 5))
    ax.bar(range(len(class_names)), f1, color=colors)
    ax.set_xticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=90, fontsize=7)
    ax.set_ylabel("F1 Score")
    ax.set_ylim(0, 1.05)
    ax.axhline(y=0.7, color="#2ecc71", linestyle="--", alpha=0.6, label="Seuil 70%")
    ax.axhline(y=f1.mean(), color="white", linestyle="-", alpha=0.8,
               label=f"Moyenne : {f1.mean():.3f}")
    ax.legend(fontsize=8)
    ax.set_title(f"F1 par race — epoch {epoch + 1}", fontsize=9)
    plt.tight_layout()
    writer.add_figure("Metrics/F1_par_race", fig, epoch)
    plt.close(fig)

    writer.add_scalar("Metrics/mean_F1_breed", float(f1.mean()), epoch)
    writer.add_scalar("Metrics/mean_Precision_breed", float(precision.mean()), epoch)
    writer.add_scalar("Metrics/mean_Recall_breed", float(recall.mean()), epoch)

    return {"precision": precision, "recall": recall, "f1": f1}


# =========================
# RAPPORT TEXTE FINAL
# =========================
def print_classification_report(labels, preds, class_names):
    print("\n" + "=" * 60)
    print("RAPPORT DE CLASSIFICATION — RACE")
    print("=" * 60)
    print(classification_report(labels, preds, target_names=class_names, zero_division=0))


# =========================
# SAVE CONFUSION MATRIX (fichier)
# =========================
def save_confusion_matrix(labels, preds, classes, save_path, title):
    cm = confusion_matrix(labels, preds)
    fig_size = max(6, len(classes) // 2)

    plt.figure(figsize=(fig_size, fig_size))
    plt.imshow(cm)
    plt.title(title)
    plt.colorbar()

    tick_marks = range(len(classes))
    plt.xticks(tick_marks, classes, rotation=90, fontsize=6)
    plt.yticks(tick_marks, classes, fontsize=6)

    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


# =========================
# SAVE MODEL
# =========================
def save_model(model, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save(model.state_dict(), path)