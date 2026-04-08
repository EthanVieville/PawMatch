# scraper/parser_fiche_full.py

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
import re


# -------------------
# 🔥 EXTRACTION GÉNÉRIQUE (clé → valeur)
# -------------------
def extract_info(soup, label_name):
    labels = soup.select("p.c-banner-animal_info-key")

    for label in labels:
        if label.text.strip().lower() == label_name.lower():
            parent = label.find_parent()

            if parent:
                value_tag = parent.select_one("p.c-banner-animal_info-value")

                if value_tag:
                    return value_tag.text.strip().lower()

    return None


def parse_fiche(driver, url):
    driver.get(url)

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
    except:
        print(f"❌ Timeout: {url}")
        return None

    soup = BeautifulSoup(driver.page_source, "lxml")

    # -------------------
    # NOM
    # -------------------
    name_tag = soup.find("h1")
    name = name_tag.text.strip() if name_tag else "unknown"

    # -------------------
    # ESPÈCE (DYNAMIQUE)
    # -------------------
    species = extract_info(soup, "Espèce")

    # -------------------
    # RACE (DYNAMIQUE)
    # -------------------
    race = extract_info(soup, "Race")

    # -------------------
    # SEXE + DATE NAISSANCE
    # -------------------
    sex = "unknown"
    birth_date = None

    info_blocks = soup.select("p.c-banner-animal_info-more")

    for p in info_blocks:
        text = p.text.strip().lower()

        if "femelle" in text:
            sex = "femelle"
        elif "male" in text or "mâle" in text:
            sex = "male"

        if "né" in text:
            match = re.search(r"\d{4}-\d{2}-\d{2}", text)
            if match:
                birth_date = match.group()

    # -------------------
    # AGE
    # -------------------
    age = None

    if birth_date:
        try:
            birth = datetime.strptime(birth_date, "%Y-%m-%d")
            today = datetime.today()

            age = today.year - birth.year - (
                (today.month, today.day) < (birth.month, birth.day)
            )
        except:
            pass

    # -------------------
    # 🏠 REFUGE
    # -------------------
    refuge = None

    refuge_tag = soup.select_one("a[href*='/etablissement/']")

    if refuge_tag:
        refuge = refuge_tag.text.strip()

    # -------------------
    # DESCRIPTION CLEAN
    # -------------------
    description = ""

    for p in soup.find_all("p"):
        text = p.text.strip()

        if (
            len(text) > 40
            and "newsletter" not in text.lower()
            and "je souhaite adopter" not in text.lower()
            and "participation financière" not in text.lower()
        ):
            description += text + "\n"

    description = " ".join(description.split())

    # -------------------
    # INCOMPATIBILITÉS
    # -------------------
    incompatibilities = []

    for txt in soup.stripped_strings:
        txt = txt.lower()

        if "pas ok enfants" in txt:
            incompatibilities.append("enfants")
        if "pas ok chiens" in txt:
            incompatibilities.append("chiens")
        if "pas ok chats" in txt:
            incompatibilities.append("chats")

    incompatibilities = list(set(incompatibilities))

    # -------------------
    # IMAGE PRINCIPALE
    # -------------------
    images = []

    main_img = soup.select_one("img[src*='/uploads/animals/']")

    if main_img:
        src = main_img.get("src")

        if src.startswith("/"):
            src = "https://www.la-spa.fr" + src

        images = [src]

    # -------------------
    # OUTPUT FINAL
    # -------------------
    return {
        "url": url,
        "name": name,
        "species": species,
        "race": race,
        "refuge": refuge,
        "sex": sex,
        "birth_date": birth_date,
        "age": age,
        "description": description,
        "incompatibilities": incompatibilities,
        "images": images,
    }