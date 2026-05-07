import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from crawler_links import get_animal_links
from driver import init_driver
from parser_fiche_full import parse_fiche
from storage import save_animal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

MAX_PAGES = int(os.environ.get("MAX_PAGES", "10"))
NUM_WORKERS = int(os.environ.get("NUM_WORKERS", "4"))
DATA_PATH = os.environ.get("DATA_PATH", "data")


def _chunk_list(lst, n):
    """Split lst into n roughly equal chunks."""
    k, rem = divmod(len(lst), n)
    chunks, start = [], 0
    for i in range(n):
        end = start + k + (1 if i < rem else 0)
        if start < end:
            chunks.append(lst[start:end])
        start = end
    return chunks


def _worker(urls):
    driver = init_driver()
    results = []
    try:
        for url in urls:
            try:
                data = parse_fiche(driver, url)
                if data:
                    results.append(data)
            except Exception as e:
                logger.error("Failed to parse %s: %s", url, e)
    finally:
        driver.quit()
    return results


def run():
    logger.info("Starting scraper — max_pages=%d workers=%d data_path=%s",
                MAX_PAGES, NUM_WORKERS, DATA_PATH)

    links = get_animal_links(max_pages=MAX_PAGES)
    logger.info("%d animals to scrape", len(links))

    if not links:
        logger.warning("No links found, exiting")
        return

    chunks = _chunk_list(links, NUM_WORKERS)

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(_worker, chunk) for chunk in chunks]

        with tqdm(total=len(links), desc="Scraping animals") as pbar:
            for future in as_completed(futures):
                try:
                    results = future.result()
                except Exception as e:
                    logger.error("Worker failed: %s", e)
                    continue

                for data in results:
                    species = data.get("species") or "inconnu"
                    try:
                        save_animal(data, species, base_path=DATA_PATH)
                    except Exception as e:
                        logger.error("Failed to save %s: %s", data.get("name"), e)
                    pbar.update(1)

    logger.info("Scraping complete")


if __name__ == "__main__":
    run()
