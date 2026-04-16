# dl_models/utils/tools_models.py

import torch
import os
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt


# =========================
# TRAIN LOOP
# =========================
def train_one_epoch(model, loader, optimizer, type_loss_fn, color_loss_fn, device):
    model.train()

    total_loss = 0
    correct_type = 0
    total_type = 0
    correct_color = 0
    total_color = 0

    for images, types, colors in loader:
        images = images.to(device)
        types = types.to(device)
        colors = colors.to(device)

        pred_type, pred_color = model(images)

        loss_type = type_loss_fn(pred_type, types)
        loss_color = color_loss_fn(pred_color, colors)

        loss = loss_type + 0.5 * loss_color

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

        pred_type_labels = pred_type.argmax(dim=1)
        pred_color_labels = pred_color.argmax(dim=1)

        correct_type += (pred_type_labels == types).sum().item()
        correct_color += (pred_color_labels == colors).sum().item()

        total_type += types.size(0)
        total_color += colors.size(0)

    total_loss /= len(loader)

    return {
        "loss": total_loss,
        "type_acc": correct_type / total_type,
        "color_acc": correct_color / total_color
    }


# =========================
# VALIDATION LOOP
# =========================
def evaluate(model, loader, type_loss_fn, color_loss_fn, device):
    model.eval()

    val_loss = 0
    correct_type = 0
    total_type = 0
    correct_color = 0
    total_color = 0

    all_type_preds = []
    all_type_labels = []

    all_color_preds = []
    all_color_labels = []

    with torch.no_grad():
        for images, types, colors in loader:
            images = images.to(device)
            types = types.to(device)
            colors = colors.to(device)

            pred_type, pred_color = model(images)

            loss = type_loss_fn(pred_type, types) + color_loss_fn(pred_color, colors)
            val_loss += loss.item()

            pred_type_labels = pred_type.argmax(dim=1)
            pred_color_labels = pred_color.argmax(dim=1)

            correct_type += (pred_type_labels == types).sum().item()
            correct_color += (pred_color_labels == colors).sum().item()

            total_type += types.size(0)
            total_color += colors.size(0)

            all_type_preds.extend(pred_type_labels.cpu().numpy())
            all_type_labels.extend(types.cpu().numpy())

            all_color_preds.extend(pred_color_labels.cpu().numpy())
            all_color_labels.extend(colors.cpu().numpy())

    val_loss /= len(loader)

    return {
        "loss": val_loss,
        "type_acc": correct_type / total_type,
        "color_acc": correct_color / total_color,
        "type_preds": all_type_preds,
        "type_labels": all_type_labels,
        "color_preds": all_color_preds,
        "color_labels": all_color_labels,
    }


# =========================
# CONFUSION MATRIX SAVE
# =========================
def save_confusion_matrix(labels, preds, classes, save_path, title):
    cm = confusion_matrix(labels, preds)

    plt.figure(figsize=(6, 6))
    plt.imshow(cm)
    plt.title(title)
    plt.colorbar()

    tick_marks = range(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

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