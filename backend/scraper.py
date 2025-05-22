from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
import pandas as pd
import os
from datetime import datetime
from fake_useragent import UserAgent

def ensure_screenshot_dir(person_name):
    # Create base screenshots directory if it doesn't exist
    base_dir = "screenshots"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    
    # Create person-specific directory
    person_dir = os.path.join(base_dir, person_name)
    if not os.path.exists(person_dir):
        os.makedirs(person_dir)
    return person_dir

def take_viewport_screenshots(driver, screenshot_dir, page_num):
    # Get the total height of the page
    total_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")
    
    scroll_position = 0
    screenshot_count = 0
    
    while scroll_position < total_height:
        # Take screenshot of current viewport
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"page{page_num}_viewport{screenshot_count}_{timestamp}.png"
        driver.save_screenshot(os.path.join(screenshot_dir, filename))
        
        # Scroll down one viewport
        scroll_position += viewport_height
        driver.execute_script(f"window.scrollTo(0, {scroll_position});")
        time.sleep(0.5)  # Wait for any lazy-loaded content
        screenshot_count += 1

def check_suspicious_content(title, description):
    suspicious_keywords = {
        'sanction', 'sanctions', 'sanctioned',
        'terror', 'terrorism', 'terrorist',
        'money laundering', 'laundering',
        'criminal', 'fraud', 'fraudulent',
        'illegal', 'illicit', 'trafficking',
        'ofac', 'blacklist', 'blacklisted',
        'blocked', 'sdn', 'violation'
    }
    
    # Convert to lowercase for case-insensitive matching
    text = (title + " " + description).lower()
    
    # Check if any of the suspicious keywords are in the text
    return any(keyword in text for keyword in suspicious_keywords)

def google_search_links(query, max_results=20, headless=True, person_name=None):
    options = Options()

    # ua = UserAgent(browsers=["Google", "Chrome"], os="Windows", min_version=133.0, platforms="desktop")
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--log-level=3")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"user-agent={ua}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)

    # Create screenshot directory
    if not person_name:
        person_name = query.strip('"')  # Extract person's name from query if not provided
    screenshot_dir = ensure_screenshot_dir(person_name)

    # # Accept cookies if shown
    # try:
    #     consent_btn = driver.find_element(By.XPATH, "//button[contains(., 'I agree') or contains(., 'Accept all')]")
    #     consent_btn.click()
    #     time.sleep(1)
    # except:
    #     pass  # No consent prompt shown

    # time.sleep(2)

    links = set()
    titles = []
    descriptions = []
    flags = []  # List to store suspicious content flags
    page = 0
    driver.get("https://www.example.com/")
    time.sleep(2)
    return driver.find_element(By.TAG_NAME, "h1").text
    while len(links) < max_results and page < 5:
        url = f"https://www.google.com/search?q={query}&start={page * 10}"
        driver.get(url)
        time.sleep(2)
        # Take screenshots of current page
        take_viewport_screenshots(driver, screenshot_dir, page)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        results = driver.find_elements(By.CLASS_NAME, "MjjYud")
        for result in results:
            try:
                title = result.find_element(By.TAG_NAME, "a").text
                link = result.find_element(By.TAG_NAME, "a").get_attribute("href")
                description = result.find_element(By.CLASS_NAME, "VwiC3b").text

                if link not in links:
                    links.add(link)
                    titles.append(title)
                    descriptions.append(description)
                    # Check if the result contains suspicious content
                    flags.append(check_suspicious_content(title, description))

                    if len(links) >= max_results:
                        break
            except Exception as e:
                print(e)
                continue
        page += 1

    driver.quit()
    return list(links), list(titles), list(descriptions), flags


def find_suspicious_links(person_name):
    # Define the query for Google search
    query = f'"{person_name}"'

    # Perform the search and get the results
    # links, titles, descriptions, flags = google_search_links(query, person_name=person_name)

    return google_search_links(query, person_name=person_name)
    # Create a DataFrame to store the results
    # df = pd.DataFrame({
    #     'Links': links,
    #     'Titles': titles,
    #     'Descriptions': descriptions,
    #     'Suspicious': flags
    # })
    # Save the DataFrame to a CSV file
    # df.to_csv(f'{person_name}.csv', index=False)
    
    # Filter out suspicious links
    sus = df[df['Suspicious'] == True]
    return sus['Links'].tolist()

# Example usage
if __name__ == "__main__":
    person = "Mohammad Taher Anwari"
    print(find_suspicious_links(person))