# dl_models/utils/paths.py

from pathlib import Path

# root du projet : PA5emeAnn-e/
ROOT_DIR = Path(__file__).resolve().parents[2]

PET_DATASET_DIR = ROOT_DIR / "dl_models" / "datasets" / "oxford-iiit-pet"

PET_IMAGES_DIR = PET_DATASET_DIR / "images"
PET_ANNOTATIONS_DIR = PET_DATASET_DIR / "annotations"

PET_TRAIN_FILE = PET_ANNOTATIONS_DIR / "trainval.txt"
PET_TEST_FILE = PET_ANNOTATIONS_DIR / "test.txt"