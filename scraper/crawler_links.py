# scraper/crawler_links.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def init_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # 🔥 désactiver images + CSS (gros gain)
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


def get_animal_links(max_pages=5):
    driver = init_driver()

    all_links = []

    for page in range(1, max_pages + 1):
        if page == 1:
            url = "https://www.la-spa.fr/adoption/"
        else:
            url = f"https://www.la-spa.fr/adoption/?page={page}"

        print(f"📄 Page {page}")

        driver.get(url)

        # 🔥 ATTENTE INTELLIGENTE (remplace sleep)
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/animal/')]"))
            )
        except:
            print("⚠️ Timeout page, on continue")

        elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/animal/')]")

        page_links = []

        for el in elements:
            href = el.get_attribute("href")

            if href and "/animal/" in href:
                page_links.append(href)

        page_links = list(set(page_links))

        print(f"👉 {len(page_links)} liens trouvés")

        # 🔥 arrêt automatique si page vide
        if not page_links:
            print("🛑 Fin pagination")
            break

        all_links.extend(page_links)

    driver.quit()

    all_links = list(set(all_links))

    print(f"\n✅ Total: {len(all_links)} fiches uniques")

    return all_links