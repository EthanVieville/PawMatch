import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from driver import init_driver

logger = logging.getLogger(__name__)

BASE_URL = "https://www.30millionsdamis.fr"
LISTING_URL = BASE_URL + "/jagis/jadopte-un-animal/adoption/{type}/"
SPECIES_TYPES = ["chien", "chat", "autre"]

# MAX_PAGES applies per species type: MAX_PAGES=3 ≈ 90 animals (3 types × ~10/page × 3 pages)
LINK_XPATH = "//a[contains(@href, '/jadopte-un-animal/adopter/')]"


def get_animal_links(max_pages=3):
    driver = init_driver()
    all_links = []

    try:
        for species_type in SPECIES_TYPES:
            base = LISTING_URL.format(type=species_type)

            for page in range(1, max_pages + 1):
                if page == 1:
                    url = base
                else:
                    url = f"{base}?tx_ameosadoption_adoptions-list%5BcurrentPage%5D={page}"

                logger.info("Crawling %s page %d: %s", species_type, page, url)
                driver.get(url)

                try:
                    WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.XPATH, LINK_XPATH))
                    )
                except Exception:
                    logger.warning("%s page %d: timeout waiting for links, stopping", species_type, page)
                    break

                elements = driver.find_elements(By.XPATH, LINK_XPATH)
                page_links = list({
                    el.get_attribute("href")
                    for el in elements
                    if el.get_attribute("href")
                })

                if not page_links:
                    logger.info("%s page %d: no links found, end of pagination", species_type, page)
                    break

                logger.info("%s page %d: %d links found", species_type, page, len(page_links))
                all_links.extend(page_links)

    finally:
        driver.quit()

    unique_links = list(set(all_links))
    logger.info("Total: %d unique animal pages", len(unique_links))
    return unique_links
