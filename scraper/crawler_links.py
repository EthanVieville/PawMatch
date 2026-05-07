import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from driver import init_driver

logger = logging.getLogger(__name__)

BASE_URL = "https://www.la-spa.fr/adoption/"


def get_animal_links(max_pages=5):
    driver = init_driver()
    all_links = []

    try:
        for page in range(1, max_pages + 1):
            url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
            logger.info("Crawling page %d: %s", page, url)

            driver.get(url)

            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/animal/')]"))
                )
            except Exception:
                logger.warning("Page %d: timeout waiting for animal links, stopping pagination", page)
                break

            elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/animal/')]")
            page_links = list({
                el.get_attribute("href")
                for el in elements
                if el.get_attribute("href") and "/animal/" in el.get_attribute("href")
            })

            if not page_links:
                logger.info("Page %d: no links found, end of pagination", page)
                break

            logger.info("Page %d: %d links found", page, len(page_links))
            all_links.extend(page_links)

    finally:
        driver.quit()

    unique_links = list(set(all_links))
    logger.info("Total: %d unique animal pages", len(unique_links))
    return unique_links
