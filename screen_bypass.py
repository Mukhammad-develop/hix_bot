import undetected_chromedriver as uc
import pickle
import os
import time
import json
import random
# import pyautogui

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === CONFIG ===
SESSION_FILE = "cookies.pkl"
LOCALSTORAGE_FILE = "local_storage.json"
PROFILE_FOLDER = "hix-user-profile"
TARGET_URL = "https://hix.ai/app/bypass-ai-detection/dashboard"

# Global driver instance
_driver = None
# pyautogui.FAILSAFE = False


def launch_driver_once():
    global _driver
    if _driver is None:
        print("🚀 Launching browser directly to dashboard...")
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.user_data_dir = os.path.abspath(PROFILE_FOLDER)
        _driver = uc.Chrome(options=options, use_subprocess=True)

        # Skip hix.ai and go directly to bypass dashboard
        _driver.get(TARGET_URL)
        time.sleep(random.uniform(3, 7))  # Random sleep between 3 to 7 seconds

        # Load session data
        load_cookies(_driver)
        load_localstorage(_driver)

        # Refresh to apply cookies & storage
        _driver.get(TARGET_URL)
        time.sleep(random.uniform(3, 7))  # Random sleep between 3 to 7 seconds

    return _driver


def quit_driver():
    global _driver
    if _driver:
        print("💾 Saving session data...")
        save_cookies(_driver)
        save_localstorage(_driver)
        print("🛑 Closing browser...")
        _driver.quit()
        _driver = None


def save_cookies(driver):
    with open(SESSION_FILE, "wb") as f:
        pickle.dump(driver.get_cookies(), f)


def load_cookies(driver):
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "rb") as f:
            cookies = pickle.load(f)
        for cookie in cookies:
            cookie.pop("expiry", None)
            try:
                driver.add_cookie(cookie)
            except:
                pass


def save_localstorage(driver):
    data = driver.execute_script(
        "let items = {}; for (let i = 0; i < localStorage.length; i++) { "
        "let key = localStorage.key(i); items[key] = localStorage.getItem(key); } return items;"
    )
    with open(LOCALSTORAGE_FILE, "w") as f:
        json.dump(data, f)


def load_localstorage(driver):
    if os.path.exists(LOCALSTORAGE_FILE):
        with open(LOCALSTORAGE_FILE, "r") as f:
            data = json.load(f)
        for key, value in data.items():
            driver.execute_script(f"localStorage.setItem('{key}', `{value}`);")


def paste_text(driver, text):
    wait = WebDriverWait(driver, 20)
    editor = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR, 'div[contenteditable="true"].ProseMirror'
    )))
    driver.execute_script("""
        const div = arguments[0];
        div.innerHTML = `<p>${arguments[1]}</p>`;
        const event = new Event('input', { bubbles: true });
        div.dispatchEvent(event);
    """, editor, text)


def click_humanize(driver):
    wait = WebDriverWait(driver, 20)
    button = wait.until(EC.element_to_be_clickable((
        By.XPATH, '//button[span[text()="Humanize"]]'
    )))
    button.click()


def get_output(driver):
    wait = WebDriverWait(driver, 30)
    result = wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR,
        'div[contenteditable="false"].ProseMirror'
    )))
    time.sleep(random.uniform(1, 3))  # Random sleep between 1 to 3 seconds
    return result.text


def humanize_from_hix(text):
    driver = launch_driver_once()

    try:
        paste_text(driver, text)
        click_humanize(driver)
        output = get_output(driver)

        return { "input": text, "humanized": output }

    except Exception as e:
        return False


if __name__ == "__main__":
    try:
        # Your main code here
        launch_driver_once()
        # Keep the script running
        input("Press Enter to quit...")
    finally:
        quit_driver()
    