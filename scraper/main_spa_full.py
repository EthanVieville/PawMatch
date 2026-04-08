# scraper/main_spa_final.py

from crawler_links import get_animal_links
from parser_fiche_full import parse_fiche
from storage import save_animal

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.set_page_load_timeout(10)

    return driver


# 🔥 worker avec driver persistant
def worker(urls):
    driver = init_driver()
    results = []

    for url in urls:
        try:
            data = parse_fiche(driver, url)
            if data:
                results.append(data)
        except Exception as e:
            print(f"❌ {url} -> {e}")

    driver.quit()
    return results


def chunk_list(lst, n):
    """Découpe liste en n chunks"""
    k = len(lst) // n
    return [lst[i*k:(i+1)*k] for i in range(n-1)] + [lst[(n-1)*k:]]


def run():
    links = get_animal_links(max_pages=10)

    print(f"👉 {len(links)} animaux à scraper")

    num_workers = 4
    chunks = chunk_list(links, num_workers)

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker, chunk) for chunk in chunks]

        # 🔥 tqdm corrigé
        with tqdm(total=len(links), desc="🐾 Scraping animaux") as pbar:
            for future in as_completed(futures):
                results = future.result()

                for data in results:
                    save_animal(data, data["species"])
                    pbar.update(1)


if __name__ == "__main__":
    run()