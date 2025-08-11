import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC

# For static content scraping
import re, random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Global Variables
afile = open("useragents.txt")

# Functions
def random_line(afile):
    lines = afile.readlines()
    return random.choice(lines)
# save_to_file
def save_to_file(filename, data_set):
    with open(filename, "w") as f:
        for item in sorted(data_set):
            f.write(f"{item}\n")

# tracked URLs/Emails
def load_tracked_set(filename):
    try:
        with open(filename, "r") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def is_google_redirect(url):
    return any(x in url for x in ["google.com/aclk", "google.com/url"])

def get_final_url_via_selenium(redirect_url):
    try:
        driver.get(redirect_url)
        wait(driver, 10).until(lambda d: d.current_url != redirect_url)
        final_url = driver.current_url
    except Exception as e:
        print("Error getting final URL:", e)
        final_url = None
    return final_url

def fetch_emails(url): # fetch_emails
    """Fetch and return a set of emails from the given URL."""
    try:
        headers = random_line(afile).rstrip()
        time.sleep(1 + random.uniform(0, 1))
        r  = requests.get(url, headers={'User-Agent': headers}, timeout = 100)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        return set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", soup.get_text()))
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return set()

# find_relevant_page (contact us, career, jobs etc.)
def find_relevant_pages(base_url):
    """
    Find all pages likely to contain contact or career info,
    using English and German keywords.
    Returns a list of absolute URLs.
    """
    keywords = [
        "contact", "kontakt", "about", "über", "impressum", 
        "job", "career", "karriere", "stellenangebot", "jobs", "stellen"
    ]

    relevant_urls = set()
    try:
        r = requests.get(base_url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            text = a.get_text(strip=True).lower()

            if any(kw in href for kw in keywords) or any(kw in text for kw in keywords):
                abs_url = urljoin(base_url, a["href"])
                relevant_urls.add(abs_url)
    except Exception as e:
        print(f"Error scanning homepage for relevant pages: {e}")

    return list(relevant_urls)

# selenium Initialize Chrome WebDriver
options = Options()
# options.add_argument('--headless')  # optional
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://www.google.com/maps/search/berlin+restaurants/@52.516243,13.3406937,13z/data=!3m1!4b1?entry=ttu")
# Main Logic .......................................

try:
    tracked_emails = load_tracked_set("tracked_emails.txt")
    tracked_websites = load_tracked_set("tracked_websites.txt")
    # Accept cookies
    try:
        accept_btn = wait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Alle akzeptieren')]"))
        )
        accept_btn.click()
        print("✅ Cookies accepted")
    except:
        print("⚠️ No cookie popup found")

    # Scrollable results container
    scrollable_div = wait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//div[@role='feed']"))
    )

    # Track processed links
    processed = set()


    while True:
        listings = scrollable_div.find_elements(By.XPATH, ".//a[contains(@class,'hfpxzc')]")
        if not listings:
            break

        for listing in listings:
            href = listing.get_attribute("href")
            if href in processed:
                continue

            processed.add(href)

            driver.execute_script("arguments[0].scrollIntoView();", listing)
            time.sleep(1 + random.uniform(0, 1))
            driver.execute_script("arguments[0].click();", listing)
            time.sleep(1 + random.uniform(0, 1))

            # Extract restaurant name
            try:
                name = wait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(@class,'DUwDvf')]"))
                ).text
            except:
                name = None

            # Extract website
            try:
                website_elem = driver.find_element(By.XPATH, "//a[contains(@aria-label, 'Website')]")
                raw_url = website_elem.get_attribute("href")

                if is_google_redirect(raw_url):
                    print(f"⚠️ Redirect URL detected: {raw_url}")
                    url = get_final_url_via_selenium(raw_url)
                    website = url.split('?')[0] if url else None
                else:
                    website = raw_url.split('?')[0]
                
                if website in tracked_websites:
                    print(f"⚠️ Skipping {website} — already processed")
                    continue

            except Exception as e:
                print(f"Error extracting website: {e}")
                website = None

            print(f"\n\n")
            print("=" * 40)
            print(f"Name: {name or 'Unknown'}")
            print(f"Website: {website}")

            if website:
                # Save website after processing emails
                tracked_websites.add(website)
                save_to_file("tracked_websites.txt", tracked_websites)

                # Fetch emails from homepage
                emails = fetch_emails(website)
                new_emails = emails - tracked_emails

                if new_emails:
                    print(f"New emails found on {website}: {new_emails}")
                    tracked_emails.update(new_emails)
                    save_to_file("tracked_emails.txt", tracked_emails)
                    for i, email in enumerate(new_emails, 1):
                        print(f"email {i}: {email}")
                else: 
                    print(f"⚠️ No emails found on homepage of {website}")

                # Check other relevant pages too
                print(f"Searching for relevant pages on {website}...")        
                relevant_pages = find_relevant_pages(website)
                print(f"Found {len(relevant_pages)} relevant pages.")
                if relevant_pages:
                    for url in relevant_pages:
                        relevant_emails = fetch_emails(url)
                        new_emails = relevant_emails - tracked_emails
                        if new_emails:
                            print(f"New emails found on {website}: {new_emails}")
                            tracked_emails.update(new_emails)
                            save_to_file("tracked_emails.txt", tracked_emails)
                            for i, email in enumerate(new_emails, 1):
                                print(f"email {i}: {email}")
                            break  # stop after finding emails
                    else:
                        # no break happened → no emails found on any relevant page
                        print("⚠️ No emails found on any relevant page.")
                else:
                    print("⚠️ No relevant pages found.")

            # Return to list
            driver.execute_script("arguments[0].scrollIntoView();", scrollable_div)
            time.sleep(1 + random.uniform(0, 1))

        # Scroll to load more listings
        prev_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
        time.sleep(1 + random.uniform(0, 1))
        new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
        if new_height == prev_height:
            break
        print("\n\n@@@@@@@@@@@@@@@@@ Loading more listings...")

except KeyboardInterrupt:
    print("\n🛑 Interrupted by user, exiting...")
finally:
    driver.quit()