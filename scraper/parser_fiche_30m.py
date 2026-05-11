import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

BASE_URL = "https://www.30millionsdamis.fr"

_INCOMPATIBILITY_NEGATIVE = [
    "ne s'entend pas avec",
    "incompatible avec",
    "pas compatible avec",
    "ne supporte pas",
    "non compatible avec",
    "ne cohabite pas avec",
]
_INCOMPATIBILITY_KEYWORDS = {
    "enfant": "enfants",
    "enfants": "enfants",
    "chat": "chats",
    "chats": "chats",
    "chien": "chiens",
    "chiens": "chiens",
}


def _extract_label_value(soup, *label_texts):
    """Find a <li> in div.animalid whose <label> matches any of label_texts, return <p> text."""
    for li in soup.select("div.animalid ul li"):
        label = li.select_one("label")
        if not label:
            continue
        label_lower = label.text.strip().lower()
        for lt in label_texts:
            if lt.lower() in label_lower:
                p = li.select_one("p")
                return p.text.strip() if p else None
    return None


def _detect_species_from_url(url):
    url_lower = url.lower()
    if "-chien" in url_lower:
        return "chien"
    if "-chat" in url_lower:
        return "chat"
    if "-lapin" in url_lower:
        return "lapin"
    if "-nac" in url_lower:
        return "nac"
    return None


def _parse_age_from_text(text):
    if not text:
        return None
    text = text.lower()
    m = re.search(r"(\d+)\s*an", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*mois", text)
    if m:
        return max(0, int(m.group(1)) // 12)
    return None


def _parse_incompatibilities(text):
    if not text:
        return []
    seen = set()
    text_lower = text.lower()
    for phrase in _INCOMPATIBILITY_NEGATIVE:
        if phrase not in text_lower:
            continue
        idx = text_lower.find(phrase) + len(phrase)
        snippet = text_lower[idx:idx + 50]
        for kw, label in _INCOMPATIBILITY_KEYWORDS.items():
            if kw in snippet:
                seen.add(label)
    return list(seen)


def parse_fiche(driver, url):
    driver.get(url)

    try:
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.animalid"))
        )
    except Exception:
        logger.warning("Timeout loading %s — skipping", url)
        return None

    soup = BeautifulSoup(driver.page_source, "lxml")

    # Name
    name_tag = soup.select_one("div.animalid div.name div.text")
    if not name_tag:
        name_tag = soup.find("h1")
    name = name_tag.text.strip() if name_tag else "unknown"

    # Species
    species = _detect_species_from_url(url)
    if not species:
        raw = _extract_label_value(soup, "espèce", "type")
        species = raw.lower() if raw else "inconnu"

    # Race
    raw = _extract_label_value(soup, "race")
    race = raw.lower() if raw else None

    # Sex
    sex = "unknown"
    raw = _extract_label_value(soup, "sexe")
    if raw:
        r = raw.lower()
        if "femelle" in r:
            sex = "femelle"
        elif "mâle" in r or "male" in r:
            sex = "male"

    # Age
    age = _parse_age_from_text(_extract_label_value(soup, "âge", "age"))

    # Birth date
    birth_date = None
    raw = _extract_label_value(soup, "naissance")
    if raw:
        m = re.search(r"(\d{2})[/\-](\d{2})[/\-](\d{4})", raw)
        if m:
            birth_date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
            if not age:
                try:
                    birth = datetime.strptime(birth_date, "%Y-%m-%d")
                    today = datetime.today()
                    age = today.year - birth.year - (
                        (today.month, today.day) < (birth.month, birth.day)
                    )
                except ValueError:
                    pass

    # Shelter
    refuge = None
    shelter_tag = soup.select_one("div.refuge-coordonnees p strong")
    if shelter_tag:
        refuge = shelter_tag.text.strip()

    # Description — find the detail div that has h3 sections (Histoire/Caractère/Commentaire)
    # Note: div.adoptions.detail appears twice in the page; the first contains animalid,
    # the second contains the description sections.
    _DESC_NOISE = ("créer un compte", "envoyer un message", "identifiez-vous")
    description_parts = []
    for d in soup.select("div.adoptions.detail"):
        if d.find("h3"):
            for p in d.find_all("p"):
                text = p.text.strip()
                if len(text) > 20 and not any(n in text.lower() for n in _DESC_NOISE):
                    description_parts.append(text)
            break
    description = " ".join(" ".join(description_parts).split()) or None

    # Incompatibilities — scan description text
    incompatibilities = _parse_incompatibilities(description)

    # Images — primary image then any gallery images
    images = []
    primary = soup.select_one("div.animalid div.img picture img")
    if primary:
        src = primary.get("src", "")
        if src:
            images.append(BASE_URL + src if src.startswith("/") else src)

    for img in soup.select("div.photos img, div.galerie img, .slider img"):
        src = img.get("src", "")
        if not src:
            continue
        full = BASE_URL + src if src.startswith("/") else src
        if full not in images:
            images.append(full)

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
