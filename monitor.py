import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


TARGET_URL = os.environ.get("TARGET_URL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Telegram notification sent successfully.")
    except Exception as e:
        print(f"Error sending telegram message: {e}")


def check_stock():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    # Set an organic looking user agent to avoid basic blocks
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        driver.get(TARGET_URL)
        # Wait a bit for JS to populate the product details
        time.sleep(5)
        
        page_source = driver.page_source.lower()
        
        # Check against anti-bot pages
        if "verify you are human" in page_source or "captcha" in page_source:
             print("Warning: Blocked by Myntra anti-bot/verification page.")
             # Optionally return true here if you want to be notified just in case it's a false negative
             return False

        # If product explicitly says out of stock
        if "out of stock" in page_source and "notify me" in page_source:
            print("Product is definitely out of stock.")
            return False
            
        # Try to find the 'Add to Bag' button or sizing options
        try:
            # Myntra usually uses classes containing 'pdp-add-to-bag' or 'add to bag' text
            add_to_bag_xpath = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to bag') or contains(@class, 'pdp-add-to-bag')]"
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, add_to_bag_xpath))
            )
            print("Product is IN STOCK! (Add to bag button found).")
            return True
        except Exception:
            # Fallback checks if the button isn't clearly found
            if "select size" in page_source or "size-buttons-size-button" in page_source:
                print("Product sizing found, leaning towards IN STOCK.")
                return True
                
            print("Could not definitively determine stock. Assuming Out of Stock to prevent spam.")
            return False
            
    except Exception as e:
        print(f"Error checking stock: {e}")
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    if not all([TARGET_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        print("Error: Missing required environment variables (TARGET_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID).")
        exit(1)
        
    print(f"Checking stock for URL: {TARGET_URL}")
    is_in_stock = check_stock()
    
    if is_in_stock:
        message = f"🚨 <b>MYNTRA RESTOCK ALERT</b> 🚨\n\nThe item is currently in stock!\n<a href='{TARGET_URL}'>Click here to buy</a>"
        send_telegram_message(message)
    else:
        print("No actionable stock found. No notification sent.")
