import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from driver import init_driver
from storage import init_db, save_animal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

SCRAPER_SOURCE = os.environ.get("SCRAPER_SOURCE", "la-spa")
MAX_PAGES = int(os.environ.get("MAX_PAGES", "10"))
NUM_WORKERS = int(os.environ.get("NUM_WORKERS", "4"))

_SOURCES = {
    "la-spa": ("crawler_links", "parser_fiche_full"),
    "30millionsdamis": ("crawler_links_30m", "parser_fiche_30m"),
}


def _load_source_modules():
    if SCRAPER_SOURCE not in _SOURCES:
        known = ", ".join(f"'{s}'" for s in _SOURCES)
        raise ValueError(f"Unknown SCRAPER_SOURCE: '{SCRAPER_SOURCE}'. Known sources: {known}")

    crawler_mod, parser_mod = _SOURCES[SCRAPER_SOURCE]

    import importlib
    crawler = importlib.import_module(crawler_mod)
    parser = importlib.import_module(parser_mod)
    return crawler.get_animal_links, parser.parse_fiche


def _chunk_list(lst, n):
    k, rem = divmod(len(lst), n)
    chunks, start = [], 0
    for i in range(n):
        end = start + k + (1 if i < rem else 0)
        if start < end:
            chunks.append(lst[start:end])
        start = end
    return chunks


def _worker(urls, parse_fiche_fn):
    driver = init_driver()
    results = []
    try:
        for url in urls:
            try:
                data = parse_fiche_fn(driver, url)
                if data:
                    results.append(data)
            except Exception as e:
                logger.error("Failed to parse %s: %s", url, e)
    finally:
        driver.quit()
    return results


def run():
    get_animal_links, parse_fiche = _load_source_modules()

    logger.info("Initializing database")
    init_db()

    logger.info(
        "Starting scraper — source=%s max_pages=%d workers=%d",
        SCRAPER_SOURCE, MAX_PAGES, NUM_WORKERS,
    )
    links = get_animal_links(max_pages=MAX_PAGES)
    logger.info("%d animals to scrape", len(links))

    if not links:
        logger.warning("No links found, exiting")
        return

    chunks = _chunk_list(links, NUM_WORKERS)

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(_worker, chunk, parse_fiche) for chunk in chunks]

        with tqdm(total=len(links), desc=f"Scraping [{SCRAPER_SOURCE}]") as pbar:
            for future in as_completed(futures):
                try:
                    results = future.result()
                except Exception as e:
                    logger.error("Worker failed: %s", e)
                    continue

                for data in results:
                    try:
                        save_animal(data)
                    except Exception as e:
                        logger.error("Failed to save %s: %s", data.get("name"), e)
                    pbar.update(1)

    logger.info("Scraping complete")


if __name__ == "__main__":
    run()
