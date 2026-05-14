import logging
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from driver import init_driver

logger = logging.getLogger(__name__)

BASE_URL = "https://www.secondechance.org"
LISTING_URL = BASE_URL + "/animal/recherche"
SPECIES_TYPES = ["chien", "chat", "lapin"]

# Full URL ending with /animal/{slug}-{numeric_id}
_ANIMAL_LINK_RE = re.compile(r"/animal/[^/?#]+-\d+$")


def get_animal_links(max_pages=3) -> list[str]:
    """Crawl listing pages via Selenium (JS-rendered) and return unique animal URLs.

    MAX_PAGES applies per species type:
    max_pages=3 × 3 species × ~12 animals/page ≈ 108 animals.
    """
    driver = init_driver()
    all_links: list[str] = []
    seen: set[str] = set()

    try:
        for species in SPECIES_TYPES:
            for page in range(1, max_pages + 1):
                url = f"{LISTING_URL}?espece={species}&page={page}"
                logger.info("Crawling %s page %d", species, page)
                driver.get(url)

                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((
                            By.XPATH,
                            "//a[contains(@href, '/animal/') and not(contains(@href, 'recherche'))]",
                        ))
                    )
                except Exception:
                    logger.warning("%s page %d: timeout waiting for animal links, stopping", species, page)
                    break

                elements = driver.find_elements(
                    By.XPATH,
                    "//a[contains(@href, '/animal/') and not(contains(@href, 'recherche'))]",
                )

                page_links = []
                for el in elements:
                    href = el.get_attribute("href") or ""
                    href = href.split("?")[0].rstrip("/")
                    if _ANIMAL_LINK_RE.search(href) and href not in seen:
                        seen.add(href)
                        page_links.append(href)

                if not page_links:
                    logger.info("%s page %d: no links found, end of pagination", species, page)
                    break

                logger.info("%s page %d: %d links (+%d new)", species, page, len(page_links), len(page_links))
                all_links.extend(page_links)

    finally:
        driver.quit()

    logger.info("Total: %d unique animal pages", len(all_links))
    return all_links
