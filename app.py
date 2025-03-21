from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import uuid
import requests
import redis
from dotenv import load_dotenv
from ensta import Mobile  # Import Ensta API

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

# Instagram Credentials
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

# Initialize Flask app
app = Flask(__name__, template_folder="templates")

# Set downloads folder
DOWNLOADS_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

# Initialize Ensta Mobile Client
mobile = Mobile(USERNAME, PASSWORD)

# Rate Limiting Function
def is_rate_limited(ip, limit=10, duration=60):
    if redis_client:
        key = f"rate_limit:{ip}"
        try:
            count = redis_client.incr(key)
            redis_client.expire(key, duration)
            return count > limit
        except Exception:
            return False
    return False

# Function to Fetch Instagram Media URLs
def fetch_instagram_media(post_url):
    try:
        media = mobile.post(post_url)
        if media.is_video:
            return [media.video_url]
        elif media.is_image:
            return [media.image_url]
        elif media.is_album:
            return media.album_urls
    except Exception:
        pass
    return None

# Function to Download Instagram Post
def download_instagram_post(post_url):
    urls = fetch_instagram_media(post_url)
    if not urls:
        return None
    
    downloaded_files = []
    for url in urls:
        ext = "mp4" if "video" in url else "jpg"
        filename = f"instagram_{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(DOWNLOADS_FOLDER, filename)

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            downloaded_files.append(file_path)
    return downloaded_files

# Function to Download Video from Various Platforms
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
        return render_template("instagram_downloader.html")

    client_ip = request.remote_addr
    if is_rate_limited(client_ip):
        return jsonify({"error": "Rate limit exceeded. Try again later."}), 429

    post_url = request.form.get("url")
    if not post_url:
        return jsonify({"error": "No URL provided"}), 400

    filepaths = download_instagram_post(post_url)
    if filepaths:
        return send_file(filepaths[0], as_attachment=True, download_name=os.path.basename(filepaths[0]))

    return jsonify({"error": "Could not download the Instagram content"}), 500

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
