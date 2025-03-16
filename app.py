from flask import Flask, render_template, request, send_file, session, jsonify
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
app.secret_key = os.urandom(24)  # Required for session management

# Load Instagram Credentials Securely
load_dotenv()
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

DOWNLOADS_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

# ======= INSTAGRAM DOWNLOAD =======
def download_instagram_post_playwright(post_url):
    """Uses Playwright to extract Instagram video/image URL and download it."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Mobile user-agent to avoid detection
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        })

        page.goto(post_url, timeout=60000)
        time.sleep(random.randint(5, 10))  # Randomized delay to reduce detection

        media_url = None
        try:
            media_url = page.locator("video").get_attribute("src")  # Try video first
            if not media_url:
                image_element = page.wait_for_selector("article img", timeout=10000)  # Wait for the image
                if image_element:
                    media_url = image_element.get_attribute("src")  # Now assign correctly

        except Exception as e:
            print(f"Error extracting media URL: {e}")

        browser.close()

        if not media_url:
            return None  # Media extraction failed

        parsed_url = urlparse(media_url)
        filename = os.path.basename(parsed_url.path)
        filepath = os.path.join(DOWNLOADS_FOLDER, filename)

        with open(filepath, "wb") as file:
            file.write(requests.get(media_url).content)

        return filepath

def download_instagram_post_selenium(post_url, username, password):
    """Uses Selenium to log in and extract Instagram video/image URL."""
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
            if not media_url:
                media_url = driver.find_element(By.TAG_NAME, "img").get_attribute("src")
        except:
            media_url = None

        driver.quit()

        if not media_url:
            return None  # Media extraction failed

        parsed_url = urlparse(media_url)
        filename = os.path.basename(parsed_url.path)
        filepath = os.path.join(DOWNLOADS_FOLDER, filename)

        with open(filepath, "wb") as file:
            file.write(requests.get(media_url).content)

        return filepath

    except Exception as e:
        print(f"Error downloading Instagram post: {e}")
        driver.quit()
        return None

# ======= YOUTUBE DOWNLOAD =======
def download_video(post_url, quality="best", cookies_file=None):
    """Downloads videos using yt-dlp with optional cookies."""
    time.sleep(random.randint(10, 20))
    unique_filename = f"video_{uuid.uuid4().hex}.mp4"
    video_path = os.path.join(DOWNLOADS_FOLDER, unique_filename)

    # Debug: Print the download path
    print(f"Downloading video to: {video_path}")

    quality_formats = {
        "1080": "bestvideo[height<=1080]+bestaudio/best",
        "720": "bestvideo[height<=720]+bestaudio/best",
        "480": "bestvideo[height<=480]+bestaudio/best",
        "best": "best"  # Use the best available format for faster downloads
    }

    ydl_opts = {
        "format": quality_formats.get(quality, "best"),
        "outtmpl": video_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "retries": 3,  # Retry up to 3 times in case of network issues
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        },
        "cookiefile": cookies_file  # Pass the cookies file to yt-dlp
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([post_url])
        
        # Debug: Check if the file exists
        if os.path.exists(video_path):
            print(f"Video successfully downloaded to: {video_path}")
        else:
            print(f"Error: Video file not found at: {video_path}")
        
        return video_path
    except Exception as e:
        print(f"Download Error: {e}")
        return None

def handle_youtube_cookies(video_url):
    """Uses Playwright to accept YouTube cookies and returns cookie file path in Netscape format."""
    cookies_file = os.path.join(DOWNLOADS_FOLDER, "youtube_cookies.txt")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            page.goto(video_url)
            # Wait for the consent dialog to appear
            page.wait_for_selector("ytd-consent-bump-v2-lightbox", timeout=15000)  # Wait for the consent dialog
            
            # Try to click the "Accept all" button
            accept_button = page.locator("button:has-text('Accept all')")
            if accept_button.is_visible():
                accept_button.click()
            else:
                # Fallback: Try to click the "I agree" button
                page.click("button:has-text('I agree')")
            
            time.sleep(2)  # Allow cookies to be set
        except Exception as e:
            print(f"Cookie consent handling failed: {e}")
        
        # Save cookies in Netscape format
        cookies = context.cookies()
        with open(cookies_file, "w") as f:
            # Write Netscape format header
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# This file is generated by the script\n\n")
            
            for cookie in cookies:
                # Convert expiration time to Unix timestamp
                expires = int(cookie.get("expires", -1))
                if expires == -1:
                    expires = 0  # Session cookies have expires = 0
                
                # Write cookie in Netscape format
                f.write(
                    f"{cookie['domain']}\t"
                    f"{'TRUE' if cookie['domain'].startswith('.') else 'FALSE'}\t"
                    f"{cookie['path']}\t"
                    f"{'TRUE' if cookie['secure'] else 'FALSE'}\t"
                    f"{expires}\t"
                    f"{cookie['name']}\t"
                    f"{cookie['value']}\n"
                )
        
        browser.close()
    
    return cookies_file

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
@app.route("/video", methods=["POST"])
def video_downloader():
    """Handles YouTube & Instagram downloads with cookie consent for YouTube."""
    video_url = request.form.get("video_url")
    quality = request.form.get("quality", "best")

    if not video_url:
        return render_template("index.html")

    # Check if YouTube URL
    is_youtube = any(domain in video_url for domain in ["youtube.com", "youtu.be"])

    if is_youtube:
        if not session.get('yt_cookies_accepted'):
            return jsonify({"cookie_consent_required": True})
        
        # Handle YouTube download with cookies
        cookies_file = handle_youtube_cookies(video_url)
        file_path = download_video(video_url, quality, cookies_file)
    else:
        # Handle normal download
        file_path = download_video(video_url, quality)

    if file_path:
        # Debug: Print the file path before sending
        print(f"Sending file: {file_path}")
        return jsonify({"success": True, "message": "Congratulations! The video has been downloaded successfully."})
    return jsonify({"success": False, "message": "Error: Video could not be downloaded."}), 500

@app.route("/accept-cookies", methods=["POST"])
def accept_cookies():
    """Stores cookie consent in session."""
    session['yt_cookies_accepted'] = True
    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
