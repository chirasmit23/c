from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import uuid
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv  
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Initialize Flask App
app = Flask(__name__, template_folder="templates")

# Load Instagram Credentials Securely
load_dotenv()
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

if not USERNAME or not PASSWORD:
    raise ValueError("Instagram username or password not set in .env file")

DOWNLOADS_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")

#  Function to download Instagram reels/videos WITHOUT login
def scrape_instagram_reel(post_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(post_url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        video_tag = soup.find("meta", {"property": "og:video"})

        if video_tag:
            video_url = video_tag["content"]
            video_content = requests.get(video_url).content

            file_path = os.path.join(DOWNLOADS_FOLDER, f"reel_{uuid.uuid4().hex}.mp4")
            with open(file_path, "wb") as file:
                file.write(video_content)

            return file_path

    return None

#  Function to download Instagram photo posts (LOGIN required)
def download_instagram_post(post_url, username, password):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
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
        media_url = None
        try:
            media_url = driver.find_element(By.TAG_NAME, "img").get_attribute("src")  # Only photos
        except:
            pass

        if not media_url:
            raise ValueError("Failed to extract photo URL (only photos can be downloaded with login).")

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

#  Function to download YouTube or Instagram videos
def download_video(post_url, quality):
    unique_filename = f"downloaded_video_{uuid.uuid4().hex}.mp4"
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
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([post_url])
        return video_path
    except Exception as e:
        print(f"Download Error: {e}")
        return None

# Flask Routes
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

#  Instagram Downloader Route (Smart detection: Reels/videos vs. Photos)
@app.route("/instagram", methods=["POST"])
def instagram_downloader():
    post_url = request.form["url"]

    # Try downloading the video without login
    filepath = scrape_instagram_reel(post_url)

    if filepath:
        return send_file(filepath, as_attachment=True)
    
    # If not a video, require login for photo download
    username = request.form["username"]
    password = request.form["password"]
    filepath = download_instagram_post(post_url, username, password)

    if filepath:
        return send_file(filepath, as_attachment=True)
    
    return "Error: Instagram content could not be downloaded.", 500

#  YouTube/Video Downloader Route
@app.route("/video", methods=["POST"])
def video_downloader():
    video_url = request.form.get("video_url")
    quality = request.form.get("quality")

    if video_url:
        file_path = download_video(video_url, quality)
        if file_path:
            return send_file(file_path, as_attachment=True)
        return "Error: Video could not be downloaded.", 500

    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
