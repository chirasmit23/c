from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import uuid
import time
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv  
from playwright.sync_api import sync_playwright
import tempfile  # New: Temporary file handling

# Initialize Flask App
app = Flask(__name__, template_folder="templates")

# Load Instagram Credentials Securely
load_dotenv()
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

if not USERNAME or not PASSWORD:
    raise ValueError("Instagram username or password not set in .env file")

def download_instagram_post(post_url, username, password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Login to Instagram
            page.goto("https://www.instagram.com/accounts/login/")
            time.sleep(5)
            page.fill("input[name='username']", username)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")
            time.sleep(5)

            # Open the post URL
            page.goto(post_url)
            time.sleep(5)

            # Extract media URL
            media_url = page.locator("video").get_attribute("src") or page.locator("img").get_attribute("src")
            if not media_url:
                raise ValueError("Failed to extract media URL")

            # Download media to a temporary file
            response = requests.get(media_url)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            temp_file.write(response.content)
            temp_file.close()

            return temp_file.name
        except Exception as e:
            print(f"Error downloading Instagram post: {e}")
            return None
        finally:
            browser.close()

def download_video(post_url, quality):
    # Generate a temporary file path
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    video_path = temp_file.name

    quality_formats = {
        "1080": "bestvideo[height<=1080]+bestaudio/best",
        "720": "bestvideo[height<=720]+bestaudio/best",
        "480": "bestvideo[height<=480]+bestaudio/best",
        "best": "bestvideo+bestaudio/best"
    }
    video_format = quality_formats.get(quality, "bestvideo+bestaudio/best")

    ydl_opts = {
        "format": video_format,
        "outtmpl":video_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferredformat": "mp4"}] 
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

@app.route("/instagram", methods=["POST"])
def instagram_downloader():
    username = request.form["username"]
    password = request.form["password"]
    post_url = request.form["url"]

    filepath = download_instagram_post(post_url, username, password)
    if filepath:
        return send_file(filepath, as_attachment=True)
    else:
        return "Error: Instagram post could not be downloaded.", 500

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
    return "Invalid request", 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
