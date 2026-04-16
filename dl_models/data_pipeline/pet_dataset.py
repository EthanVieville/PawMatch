# dl_models/data_pipeline/pet_dataset.py

from pathlib import Path
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
import matplotlib.pyplot as plt

from dl_models.utils.paths import PET_IMAGES_DIR, PET_TRAIN_FILE, UTILS_PATH, COLORS_PT_PATH
from dl_models.utils.colors import get_dominant_color, COLOR_MAP


class PetDataset(Dataset):
    def __init__(self, images_dir, annotations_file):
        self.images_dir = Path(images_dir)
        self.data = self._load_annotations(annotations_file)
        self.colors = torch.load(COLORS_PT_PATH)

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
        ])

    def _load_annotations(self, file_path):
        data = []

        with open(file_path, "r") as f:
            for line in f:
                if line.startswith("#"):
                    continue

                parts = line.strip().split()

                image_name = parts[0] + ".jpg"
                species = int(parts[2])

                # 0 = chat, 1 = chien
                type_label = 0 if species == 1 else 1

                data.append((image_name, type_label))

        return data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        image_name, type_label = self.data[idx]

        color_label = self.colors[image_name]

        img_path = self.images_dir / image_name
        
        image = Image.open(img_path).convert("RGB")

        #get la color avant le transform
        #color_label = get_dominant_color(image)

        image = self.transform(image)

        return (
            image,
            torch.tensor(type_label, dtype=torch.long),
            torch.tensor(color_label, dtype=torch.long)
        )


# test local 

if __name__ == "__main__":

    color = False
    test = True
    if test == True:
        dataset = PetDataset(
            images_dir=PET_IMAGES_DIR,
            annotations_file=PET_TRAIN_FILE
        )

        # get [0]
        img, type_label, color_label = dataset[0]

        print("Image shape:", img.shape)
        print("Type label:", type_label)
        print("Color label:", color_label)

        img_np = img.permute(1, 2, 0).numpy()
        plt.imshow(img_np)
        plt.title(f"Type: {'Chat' if type_label == 0 else 'Chien'} | Color: {color_label} = {COLOR_MAP[color_label.item()]} ")
        plt.axis("off")
        plt.show()

        # Loader
        dataloader = DataLoader(
            dataset,
            batch_size=32,
            shuffle=True
        )

        for images, types, colors in dataloader:
            print("Batch images:", images.shape)
            print("Batch types:", types.shape)
            print("Batch colors:", colors.shape)
            break
    
    if color == True:

        dataset = PetDataset(
            images_dir=PET_IMAGES_DIR,
            annotations_file=PET_TRAIN_FILE
        )

        # script offline à lancer une fois
        colors = {}

        for image_name, _ in dataset.data:
            img = Image.open(PET_IMAGES_DIR / image_name).convert("RGB")
            colors[image_name] = get_dominant_color(img)

        # save
        
        torch.save(colors, UTILS_PATH / "pet_colors.pt")
        print(f"Colors saved at {UTILS_PATH}")
        