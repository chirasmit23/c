from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import uuid
import time
import random
import requests
from dotenv import load_dotenv
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright  

# Initialize Flask App
app = Flask(__name__, template_folder="templates")

# Load Instagram Credentials Securely
load_dotenv()
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

DOWNLOADS_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)  # Ensure download folder exists

def download_instagram_post_playwright(post_url):
    """Uses Playwright to extract Instagram media URL and download it."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(post_url, timeout=60000)
        time.sleep(random.randint(3, 6))

        media_url = None
        try:
            media_url = page.locator("video").get_attribute("src")
            if not media_url:
                media_url = page.locator("img").get_attribute("src")
        except Exception as e:
            print(f"Error extracting media URL: {e}")

        browser.close()

        if not media_url:
            return None

        parsed_url = urlparse(media_url)
        filename = os.path.basename(parsed_url.path)
        filepath = os.path.join(DOWNLOADS_FOLDER, filename)

        with open(filepath, "wb") as file:
            file.write(requests.get(media_url).content)

        return filepath

def download_video(post_url, quality="best"):
    """Downloads videos using yt-dlp."""
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

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/instagram", methods=["POST"])
def instagram_download():
    username = request.form.get("username")
    password = request.form.get("password")
    url = request.form.get("url")
    
    # Your download logic here
    success = True  # Replace with actual success condition
    file_url = "/static/downloads/video.mp4"  # Replace with actual file path

    if success:
        return jsonify({"success": True, "file_url": file_url})
    else:
        return jsonify({"success": False})
    return render_template("instagram_downloader.html")
@app.route("/video", methods=["POST"])
def video_downloader():
    """Handles YouTube & Instagram reels downloads."""
    video_url = request.form.get("video_url")
    quality = request.form.get("quality", "best")

    if not video_url:
        return jsonify({"success": False, "error": "No video URL provided"}), 400

    file_path = download_video(video_url, quality)
    if file_path:
        return jsonify({"success": True, "file_url": f"/downloads/{os.path.basename(file_path)}"})
    else:
        return jsonify({"success": False, "error": "Video could not be downloaded."})
    return render_template("index.html")
@app.route("/downloads/<filename>")
def serve_download(filename):
    """Serves downloaded files."""
    file_path = os.path.join(DOWNLOADS_FOLDER, filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
