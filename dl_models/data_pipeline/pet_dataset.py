# dl_models/data_pipeline/pet_dataset.py

from pathlib import Path
from PIL import Image
import torch
from torch.utils.data import Dataset
import torchvision.transforms as transforms

from dl_models.utils.paths import PET_IMAGES_DIR, PET_TRAIN_FILE, COLORS_PT_PATH
from dl_models.utils.colors import COLOR_MAP

# 37 races Oxford-IIIT Pet, indexées 0-36 (= CLASS-ID - 1)
# Chats : 0-11 | Chiens : 12-36
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

_AUGMENT_TRANSFORM = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
    transforms.RandomRotation(15),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

_BASE_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


class PetDataset(Dataset):
    def __init__(self, images_dir, annotations_file, augment=False):
        self.images_dir = Path(images_dir)
        self.data = self._load_annotations(annotations_file)
        self.colors = torch.load(COLORS_PT_PATH)
        self.transform = _AUGMENT_TRANSFORM if augment else _BASE_TRANSFORM

    def _load_annotations(self, file_path):
        data = []
        with open(file_path, "r") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                parts = line.strip().split()
                image_name = parts[0] + ".jpg"
                class_id = int(parts[1]) - 1   # 0-indexed (0-36)
                species = int(parts[2])
                type_label = 0 if species == 1 else 1  # 0=chat, 1=chien
                data.append((image_name, type_label, class_id))
        return data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        image_name, type_label, breed_label = self.data[idx]
        color_label = self.colors[image_name]

        img_path = self.images_dir / image_name
        image = Image.open(img_path).convert("RGB")
        image = self.transform(image)

        return (
            image,
            torch.tensor(type_label, dtype=torch.long),
            torch.tensor(color_label, dtype=torch.long),
            torch.tensor(breed_label, dtype=torch.long),
        )


# test local
if __name__ == "__main__":
    dataset = PetDataset(
        images_dir=PET_IMAGES_DIR,
        annotations_file=PET_TRAIN_FILE,
        augment=False,
    )

    img, type_label, color_label, breed_label = dataset[0]

    print("Image shape:", img.shape)
    print("Type label:", type_label.item(), "→", "Chat" if type_label == 0 else "Chien")
    print("Color label:", color_label.item(), "→", COLOR_MAP[color_label.item()])
    print("Breed label:", breed_label.item(), "→", BREED_LABELS[breed_label.item()])