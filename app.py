from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import uuid
import time
import random
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright  # Playwright added

# Initialize Flask App
app = Flask(__name__, template_folder="templates")

# Load Instagram Credentials Securely
load_dotenv()
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

DOWNLOADS_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")

# ======= INSTAGRAM DOWNLOAD (PLAYWRIGHT) =======
def download_instagram_post_playwright(post_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Run browser in the background
        page = browser.new_page()

        # Mobile user-agent to bypass login
        page.set_extra_http_headers({
           "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        })

        page.goto(post_url, timeout=60000)
        time.sleep(3)  # Wait for content to load

        try:
            media_url = page.locator("video").get_attribute("src")  # Try video first
        except:
            media_url = page.locator("img").get_attribute("src")  # If not, try image

        if not media_url:
            raise ValueError("Failed to extract media URL")

        parsed_url = urlparse(media_url)
        filename = os.path.basename(parsed_url.path)
        filepath = os.path.join(DOWNLOADS_FOLDER, filename)

        with open(filepath, "wb") as file:
            file.write(requests.get(media_url).content)

        browser.close()
        return filepath

# ======= INSTAGRAM DOWNLOAD (SELENIUM - FALLBACK) =======
def download_instagram_post_selenium(post_url, username, password):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in background
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(5)
        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)

        driver.get(post_url)
        time.sleep(5)

        try:
            media_url = driver.find_element(By.TAG_NAME, "video").get_attribute("src")
        except:
            media_url = driver.find_element(By.TAG_NAME, "img").get_attribute("src")

        if not media_url:
            raise ValueError("Failed to extract media URL")

        parsed_url = urlparse(media_url)
        filename = os.path.basename(parsed_url.path)
        filepath = os.path.join(DOWNLOADS_FOLDER, filename)

        with open(filepath, "wb") as file:
            file.write(requests.get(media_url).content)

        return filepath

    except Exception as e:
        print(f"Error downloading Instagram post: {e}")
        return None

    finally:
        driver.quit()

# ======= YOUTUBE & INSTAGRAM REELS DOWNLOAD (yt-dlp) =======
def download_instagram_post(post_url):
    """Downloads Instagram reels/posts using Playwright to bypass login requirements."""
    
    # Add delay to prevent rate limiting
    time.sleep(random.randint(10, 20))  # ⏳ Delay before request

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(post_url, timeout=60000)
        time.sleep(5)  # Give page time to load

        try:
            media_url = page.locator("img").get_attribute("src")  # Try to get image
        except:
            media_url = page.locator("video").get_attribute("src")  # If image fails, try video

        browser.close()

        if media_url:
            response = requests.get(media_url)
            filename = f"{uuid.uuid4().hex}.mp4"
            filepath = os.path.join(os.path.expanduser("~"), "Downloads", filename)

            with open(filepath, "wb") as file:
                file.write(response.content)

            return filepath
        else:
            return None
# ======= FLASK ROUTES =======
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/instagram", methods=["GET", "POST"])
def instagram_downloader():
    if request.method == "POST":
        post_url = request.form["url"]

        # Try Playwright first, then Selenium if it fails
        filepath = download_instagram_post_playwright(post_url)
        if not filepath and USERNAME and PASSWORD:
            filepath = download_instagram_post_selenium(post_url, USERNAME, PASSWORD)

        if filepath:
            return send_file(filepath, as_attachment=True)
        else:
            return "Error: Instagram post could not be downloaded.", 500

    return render_template("instagram_downloader.html")

@app.route("/video", methods=["POST"])
def video_downloader():
    video_url = request.form.get("video_url")
    quality = request.form.get("quality")

    if video_url:
        file_path = download_video(video_url, quality)
        if file_path:
            return send_file(file_path, as_attachment=True)
        else:
            return "Error: Video could not be downloaded.", 500

    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
