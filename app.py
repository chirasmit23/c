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

# Initialize Flask App
app = Flask(__name__, template_folder="templates")

# Load Instagram Credentials Securely
load_dotenv()
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

if not USERNAME or not PASSWORD:
    raise ValueError("Instagram username or password not set in .env file")

DOWNLOADS_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")

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
        try:
            media_url = driver.find_element(By.TAG_NAME, "img").get_attribute("src")
        except:
            media_url = driver.find_element(By.TAG_NAME, "video").get_attribute("src")

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

@app.route("/instagram", methods=["GET", "POST"])
def instagram_downloader():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        post_url = request.form["url"]

        filepath = download_instagram_post(post_url, username, password)
        if filepath:
            return send_file(filepath, as_attachment=True)
        else:
            return "Error: Instagram post could not be downloaded.", 500
    return render_template("instagram_downloader.html")

@app.route("/video", methods=["POST"])
def video_downloader():
    video_url = request.form.get("video_url")
    quality = request.form.get("quality")
    
    print(f"Received video URL: {video_url}")
    print(f"Selected Quality: {quality}")

    if video_url:
        file_path = download_video(video_url, quality)
        if file_path:
            return send_file(file_path, as_attachment=True)
        else:
            print("Download failed")
            return "Error: Video could not be downloaded.", 500
    return render_template("index.html")

if __name__ == "__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)
