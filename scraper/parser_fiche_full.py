import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

_DESCRIPTION_NOISE = ("newsletter", "je souhaite adopter", "participation financière")
_INCOMPATIBILITY_MAP = {
    "pas ok enfants": "enfants",
    "pas ok chiens": "chiens",
    "pas ok chats": "chats",
}


def _extract_info(soup, label_name):
    """Return the value paired with label_name in the animal info block."""
    for label in soup.select("p.c-banner-animal_info-key"):
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
    except Exception:
        logger.warning("Timeout loading %s — skipping", url)
        return None

    soup = BeautifulSoup(driver.page_source, "lxml")

    # Name
    name_tag = soup.find("h1")
    name = name_tag.text.strip() if name_tag else "unknown"

    # Species / breed
    species = _extract_info(soup, "Espèce")
    race = _extract_info(soup, "Race")

    # Sex + birth date
    sex = "unknown"
    birth_date = None

    for p in soup.select("p.c-banner-animal_info-more"):
        text = p.text.strip().lower()
        if "femelle" in text:
            sex = "femelle"
        elif "male" in text or "mâle" in text:
            sex = "male"
        if "né" in text and birth_date is None:
            match = re.search(r"\d{4}-\d{2}-\d{2}", text)
            if match:
                birth_date = match.group()

    # Age
    age = None
    if birth_date:
        try:
            birth = datetime.strptime(birth_date, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birth.year - (
                (today.month, today.day) < (birth.month, birth.day)
            )
        except ValueError:
            logger.debug("Could not parse birth date '%s' for %s", birth_date, name)

    # Shelter
    refuge = None
    refuge_tag = soup.select_one("a[href*='/etablissement/']")
    if refuge_tag:
        refuge = refuge_tag.text.strip()

    # Description
    description_parts = []
    for p in soup.find_all("p"):
        text = p.text.strip()
        if len(text) > 40 and not any(n in text.lower() for n in _DESCRIPTION_NOISE):
            description_parts.append(text)
    description = " ".join(" ".join(description_parts).split())

    # Incompatibilities
    seen = set()
    for txt in soup.stripped_strings:
        t = txt.lower()
        for key, label in _INCOMPATIBILITY_MAP.items():
            if key in t:
                seen.add(label)
    incompatibilities = list(seen)

    # Images — scope to the main animal banner to exclude "related animals" thumbnails
    # .c-banner-animal is the BEM block that wraps all per-animal info (confirmed by
    # the c-banner-animal_info-key / c-banner-animal_info-more selectors above).
    # Related-animal sections below the fold use different container classes.
    gallery_scope = soup.select_one(".c-banner-animal") or soup
    images = []
    for img in gallery_scope.select("img[src*='/uploads/animals/']"):
        src = img.get("src", "")
        if src.startswith("/"):
            src = "https://www.la-spa.fr" + src
        if src and src not in images:
            images.append(src)

    logger.debug("Parsed %s: species=%s images=%d", name, species, len(images))

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
