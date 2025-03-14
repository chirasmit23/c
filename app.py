from flask import Flask, render_template, request, jsonify, send_file
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
from playwright.sync_api import sync_playwright

# Initialize Flask App
app = Flask(__name__, template_folder="templates")

# Load Instagram Credentials Securely
load_dotenv()
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

# Proxy Configuration
PROXY = "60.183.57.76"

# Set up proxy dictionary for requests
PROXIES = {
    "http": f"http://{PROXY}",
    "https": f"http://{PROXY}",
}

DOWNLOADS_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

# ======= INSTAGRAM DOWNLOAD (PLAYWRIGHT) =======
def download_instagram_post_playwright(post_url):
    """Uses Playwright to extract Instagram video/image URL and download it via a proxy."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy={"server": f"http://{PROXY}"})
        context = browser.new_context()
        page = context.new_page()

        page.set_extra_http_headers({
           "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        })

        page.goto(post_url, timeout=60000)
        time.sleep(random.randint(5, 10))  # Delay to reduce detection

        media_url = None
        try:
            media_url = page.locator("article img").get_attribute("src")
            if not media_url:
                media_url = page.locator("div img").get_attribute("src")
        except Exception as e:
            print(f"Error extracting media URL: {e}")

        browser.close()

        if not media_url:
            return None  # Media extraction failed

        parsed_url = urlparse(media_url)
        filename = os.path.basename(parsed_url.path)
        filepath = os.path.join(DOWNLOADS_FOLDER, filename)

        with open(filepath, "wb") as file:
            file.write(requests.get(media_url, proxies=PROXIES).content)

        return filepath

# ======= INSTAGRAM DOWNLOAD (SELENIUM - FALLBACK) =======
def download_instagram_post_selenium(post_url, username, password):
    """Uses Selenium with a proxy to log in and extract Instagram media."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f'--proxy-server=http://{PROXY}')  # Proxy applied

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
            if not media_url:
                media_url = driver.find_element(By.TAG_NAME, "img").get_attribute("src")
        except:
            media_url = None

        driver.quit()

        if not media_url:
            return None

        parsed_url = urlparse(media_url)
        filename = os.path.basename(parsed_url.path)
        filepath = os.path.join(DOWNLOADS_FOLDER, filename)

        with open(filepath, "wb") as file:
            file.write(requests.get(media_url, proxies=PROXIES).content)

        return filepath

    except Exception as e:
        print(f"Error downloading Instagram post: {e}")
        driver.quit()
        return None

# ======= YOUTUBE & INSTAGRAM REELS DOWNLOAD (yt-dlp) =======
def download_video(post_url, quality="best"):
    """Downloads videos using yt-dlp with proxy support."""
    time.sleep(random.randint(10, 15))  

    unique_filename = f"video_{uuid.uuid4().hex}.mp4"
    video_path = os.path.join(DOWNLOADS_FOLDER, unique_filename)

    quality_formats = {
        "1080": "bestvideo[height<=1080]+bestaudio/best",
        "720": "bestvideo[height<=720]+bestaudio/best",
        "480": "bestvideo[height<=480]+bestaudio/best",
        "best": "bestvideo+bestaudio/best"
    }
    video_format = quality_formats.get(quality, "bestvideo+bestaudio/best")

   ydl_opts = {
    "format": video_format,
    "outtmpl": video_path,
    "merge_output_format": "mp4",
    "quiet": True,
    "proxy": "http://60.183.57.76",
    "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }
  }


    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([post_url])
        return video_path
    except Exception as e:
        print(f"Download Error: {e}")
        return None

# ======= FLASK ROUTES =======
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/instagram", methods=["GET", "POST"])
def instagram_downloader():
    """Handles Instagram downloads."""
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
    """Handles YouTube & Instagram reels downloads using yt-dlp."""
    video_url = request.form.get("video_url")
    quality = request.form.get("quality", "best")

    if video_url:
        file_path = download_video(video_url, quality)
        if file_path:
            return jsonify({"success": True, "file": file_path})
        else:
            return jsonify({"error": "Video could not be downloaded."}), 500

    return jsonify({"error": "Invalid request."}), 400
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
