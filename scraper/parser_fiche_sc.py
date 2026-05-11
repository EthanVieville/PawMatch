import logging
import re

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

BASE_URL = "https://www.secondechance.org"

_INCOMPATIBILITY_KEYWORDS = {
    "enfant": "enfants",
    "chien": "chiens",
    "chat": "chats",
}

_DESC_NOISE = (
    "créer un compte",
    "connectez-vous",
    "nous contacter",
    "formulaire d'adoption",
)


def _extract_label(soup: BeautifulSoup, *labels: str) -> str | None:
    """Return the value of the first <p><strong>Label</strong> : value</p> with exact label match."""
    for p in soup.find_all("p"):
        strong = p.find("strong")
        if not strong:
            continue
        # Strip trailing colon so "Âge:" and "Âge" both match label "âge"
        strong_text = strong.get_text(strip=True).lower().rstrip(":").strip()
        if any(strong_text == lbl.lower() for lbl in labels):
            full = p.get_text(separator=" ", strip=True)
            idx = full.find(":")
            return full[idx + 1:].strip() if idx != -1 else None
    return None


def _parse_age(text: str | None) -> int | None:
    if not text:
        return None
    t = text.lower()
    m = re.search(r"(\d+)\s*an", t)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*mois", t)
    if m:
        return max(0, int(m.group(1)) // 12)
    return None


def _species_from_url(url: str) -> str | None:
    slug = url.rstrip("/").split("/")[-1]
    return slug.split("-")[0] if slug else None


def _siblings_after(heading_div) -> list:
    """Yield siblings after a heading div, stopping at the next section heading."""
    siblings = []
    sib = heading_div.find_next_sibling()
    while sib:
        if sib.find(class_="content-title"):
            break
        siblings.append(sib)
        sib = sib.find_next_sibling()
    return siblings


def _extract_description(soup: BeautifulSoup) -> str | None:
    for el in soup.find_all(class_="content-title"):
        if "présentation" in el.get_text(strip=True).lower():
            heading_div = el.find_parent()
            if not heading_div:
                continue
            parts = []
            for sib in _siblings_after(heading_div):
                if sib.name != "p":
                    continue
                text = sib.get_text(separator=" ", strip=True)
                if len(text) > 20 and not any(n in text.lower() for n in _DESC_NOISE):
                    parts.append(text)
            if parts:
                return " ".join(parts)
    return None


def _extract_refuge(soup: BeautifulSoup) -> str | None:
    for el in soup.find_all(class_="content-title"):
        if "contact" in el.get_text(strip=True).lower():
            heading_div = el.find_parent()
            if not heading_div:
                continue
            for sib in _siblings_after(heading_div):
                a = sib.find("a")
                if a:
                    text = a.get_text(strip=True)
                    if text and len(text) > 2:
                        return text
            break
    return None


def _extract_incompatibilities(soup: BeautifulSoup) -> list[str]:
    seen: set[str] = set()
    ul = soup.find("ul", class_="particularities")
    if ul:
        for li in ul.find_all("li"):
            text = li.get_text(strip=True).lower()
            for kw, label in _INCOMPATIBILITY_KEYWORDS.items():
                if kw in text:
                    seen.add(label)
    return list(seen)


def _extract_images(soup: BeautifulSoup) -> list[str]:
    images = []
    for img in soup.select("img[src*='/uploads/anim/']"):
        src = img.get("src", "")
        if not src or "defaults" in src:
            continue
        full = BASE_URL + src if src.startswith("/") else src
        if full not in images:
            images.append(full)
    return images


def parse_fiche(driver, url: str) -> dict | None:
    """Fetch and parse an animal detail page via Selenium (JS-rendered content)."""
    driver.get(url)

    try:
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.pacifico-regular"))
        )
    except Exception:
        logger.warning("Timeout loading %s — skipping", url)
        return None

    soup = BeautifulSoup(driver.page_source, "lxml")

    h1 = soup.find("h1", class_="pacifico-regular")
    name = h1.get_text(strip=True) if h1 else "unknown"

    species = _species_from_url(url)

    race_raw = _extract_label(soup, "type", "race")
    race = race_raw.lower() if race_raw else None

    sex = "unknown"
    sex_raw = _extract_label(soup, "sexe")
    if sex_raw:
        s = sex_raw.lower()
        if "femelle" in s:
            sex = "femelle"
        elif "mâle" in s or "male" in s:
            sex = "male"

    age = _parse_age(_extract_label(soup, "âge", "age"))

    description = _extract_description(soup)
    refuge = _extract_refuge(soup)
    incompatibilities = _extract_incompatibilities(soup)
    images = _extract_images(soup)

    logger.debug("Parsed %s: species=%s desc=%s refuge=%s images=%d",
                 name, species, bool(description), bool(refuge), len(images))

    return {
        "url": url,
        "name": name,
        "species": species,
        "race": race,
        "refuge": refuge,
        "sex": sex,
        "birth_date": None,
        "age": age,
        "description": description,
        "incompatibilities": incompatibilities,
        "images": images,
    }
