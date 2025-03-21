from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import json
import uuid
import time
import requests
import redis
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Upstash Redis Setup
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=int(REDIS_PORT),
    password=REDIS_PASSWORD,
    ssl=True,
    decode_responses=True
)

# Instagram Credentials (Securely loaded from .env)
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

# Initialize Flask app
app = Flask(__name__, template_folder="templates")

# Set downloads folder
DOWNLOADS_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

# Rate Limiting Function
def is_rate_limited(ip, limit=10, duration=60):
    if redis_client:
        key = f"rate_limit:{ip}"
        with redis_client.pipeline() as pipe:
            try:
                pipe.incr(key)
                pipe.expire(key, duration)
                count = int(pipe.execute()[0])
                return count > limit
            except Exception as e:
                print(f"Redis Error: {e}")
                return False
    return False

# Function to Download Instagram Post using yt-dlp (Better than Selenium)
import json

def download_instagram_post(post_url):
    unique_filename = f"instagram_{uuid.uuid4().hex}.mp4"
    file_path = os.path.join(DOWNLOADS_FOLDER, unique_filename)
    metadata_file = file_path.replace(".mp4", ".json")

    ydl_opts = {
        "format": "best",
        "outtmpl": file_path,
        "writeinfojson": True,  #  Save metadata to JSON
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(post_url, download=True)
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False)  #  Prevent encoding errors
            print("Download Successful:", info["title"])
        return file_path if os.path.exists(file_path) else None
    except UnicodeEncodeError as e:
        print(f"Encoding Error: {e}")
    except Exception as e:
        print(f"Instagram Download Error: {e}")
    return None

# Function to Download Video (YouTube, Facebook, etc.)
def download_video(post_url, quality):
    unique_filename = f"video_{uuid.uuid4().hex}.mp4"
    video_path = os.path.join(DOWNLOADS_FOLDER, unique_filename)

    quality_formats = {
        "1080": "bestvideo[height<=1080]+bestaudio/best",
        "720": "bestvideo[height<=720]+bestaudio/best",
        "480": "bestvideo[height<=480]+bestaudio/best",
        "360": "bestvideo[height<=360]+bestaudio/best",
        "320": "worst",
        "best": "bestvideo+bestaudio/best"
    }
    video_format = quality_formats.get(quality, "bestvideo+bestaudio/best")

    ydl_opts = {
        "format": video_format,
        "outtmpl": video_path,
        "merge_output_format": "mp4",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([post_url])
        return video_path
    except Exception as e:
        print(f"Download Error: {e}")
        return None

# Flask Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/instagram", methods=["GET", "POST"])
def instagram_downloader():
    if request.method == "GET":
        return render_template("instagram_downloader.html")  # This ensures the page opens when accessed

    client_ip = request.remote_addr
    if is_rate_limited(client_ip):
        return jsonify({"error": "Rate limit exceeded. Try again later."}), 429

    post_url = request.form.get("url")
    if not post_url:
        return jsonify({"error": "No URL provided"}), 400

    filepath = download_instagram_post(post_url)
    if filepath:
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))

    return jsonify({"error": "Could not download the Instagram post"}), 500

@app.route("/video", methods=["POST"])
def video_downloader():
    client_ip = request.remote_addr
    if is_rate_limited(client_ip):
        return jsonify({"error": "Rate limit exceeded. Try again later."}), 429

    video_url = request.form.get("video_url")
    quality = request.form.get("quality", "best")

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    file_path = download_video(video_url, quality)
    if file_path:
        return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))

    return jsonify({"error": "Could not download the video"}), 500
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
