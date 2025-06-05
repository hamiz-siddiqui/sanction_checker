from selenium.webdriver.common.by import By
from selenium import webdriver
from bs4 import BeautifulSoup
from urllib.parse import quote
import time
from fake_useragent import UserAgent
from scraper import ensure_screenshot_dir, take_viewport_screenshots

def get_desktop_user_agent():
    ua = UserAgent()
    while True:
        agent = ua.random
        if "Mobile" not in agent and "Android" not in agent and "iPhone" not in agent and "Tablet" not in agent:
            return agent

def create_driver():
    ua = get_desktop_user_agent()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--log-level=3")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"user-agent={ua}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    return driver

def fetch_yandex(query, max_results=20, lang="ru,en"):
    driver = create_driver()
    screenshot_dir = ensure_screenshot_dir(query)
    page = 0
    try:
        url = f"https://yandex.com/search/?text={quote(query)}&lang={lang}"
        driver.get(url)
        time.sleep(2)

        results = []
        take_viewport_screenshots(driver, screenshot_dir, page)
        # Scroll down to load more results
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        # Parse the page
        results = driver.find_elements(By.CSS_SELECTOR, "li.serp-item")

        for result in results:
            if len(results) >= max_results:
                break
            a = result.find_element(By.CLASS_NAME, "Link").get_attribute("href")
            title = result.find_element(By.CSS_SELECTOR, "h2").text.strip()
            title = BeautifulSoup(title, "html.parser").text
            snippet_el = result.find_element(By.CLASS_NAME, "TextContainer").text.strip()
            results.append({
                "title": title,
                "link": a,
                "snippet": snippet_el
            })        
        page += 1
        return results
    except Exception as e:
        print(f"Error fetching results: {e}")
        return []
    finally:
        driver.quit()

if __name__ == "__main__":
    search_term = "Mohammad Taher Anwari"  # Example search term in Russian
    results = fetch_yandex(search_term, max_results=20)
    for i, item in enumerate(results, 1):
        print(f"{i}. {item['title']}\n   {item['link']}\n   {item['snippet']}\n")
