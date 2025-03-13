from flask import Flask, render_template, request, send_file
import yt_dlp
import os
import uuid
import logging
from urllib.parse import urlparse
from dotenv import load_dotenv

# Initialize Flask App
app = Flask(__name__, template_folder="templates")

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load Instagram Credentials Securely
load_dotenv()
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

if not USERNAME or not PASSWORD:
    logger.warning(
        "Instagram username or password not set in .env file. Login-based downloads may not work."
    )

DOWNLOADS_FOLDER = "/tmp"  # Use /tmp for server environments


def is_instagram_url(url):
    """Checks if a URL is an Instagram URL."""
    parsed_url = urlparse(url)
    return parsed_url.netloc in ("www.instagram.com", "instagram.com")


def download_instagram_media(url, username=None, password=None):
    """
    Downloads Instagram Reels/videos without login if possible,
    otherwise uses login for posts that require it.
    """
    try:
        ydl_opts = {
            "outtmpl": os.path.join(DOWNLOADS_FOLDER, "%(id)s.%(ext)s"),
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "quiet": True,
            "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        }

        if username and password:
            ydl_opts["username"] = username
            ydl_opts["password"] = password

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            info_dict = ydl.extract_info(url, download=False)
            filename = ydl.prepare_filename(info_dict)
        return filename
    except yt_dlp.DownloadError as e:
        logger.error(f"Download Error: {e}")
        error_message = str(e).lower()
        if "login required" in error_message or "rate limit" in error_message:
            return "Error: This Instagram content requires login or is rate-limited. Public content only is downloadable."
        else:
            return "Error: Instagram media could not be downloaded."
    except Exception as e:
        logger.error(f"Error downloading Instagram media: {e}")
        return "An unexpected error occurred."


def download_video(post_url, quality):
    """Downloads videos using yt-dlp."""
    unique_filename = f"downloaded_video_{uuid.uuid4().hex}.mp4"
    video_path = os.path.join(DOWNLOADS_FOLDER, unique_filename)

    quality_formats = {
        "1080": "bestvideo[height<=1080]+bestaudio/best",
        "720": "bestvideo[height<=720]+bestaudio/best",
        "480": "bestvideo[height<=480]+bestaudio/best",
        "best": "bestvideo+bestaudio/best",
    }
    video_format = quality_formats.get(quality, "bestvideo+bestaudio/best")

    ydl_opts = {
        "format": video_format,
        "outtmpl": video_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([post_url])
        return video_path
    except yt_dlp.DownloadError as e:
        logger.error(f"Download Error: {e}")
        return "Error: Video could not be downloaded."
    except Exception as e:
        logger.error(f"Download Error: {e}")
        return "Error: An unexpected error occurred."


# Flask Routes
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/instagram", methods=["GET", "POST"])
def instagram_downloader():
    if request.method == "POST":
        post_url = request.form["url"]
        username = request.form.get("username")  # Use get() to avoid KeyError
        password = request.form.get("password")  # Use get() to avoid KeyError

        if is_instagram_url(post_url):
            filepath = download_instagram_media(post_url, username, password)
            if filepath and "Error:" not in filepath:  # Check for error message
                return send_file(filepath, as_attachment=True)
            else:
                return filepath, 500  # Return the error message
        else:
            return "Error: Invalid Instagram URL.", 400
    return render_template("instagram_downloader.html")


@app.route("/video", methods=["POST"])
def video_downloader():
    video_url = request.form.get("video_url")
    quality = request.form.get("quality")

    logger.info(f"Received video URL: {video_url}")
    logger.info(f"Selected Quality: {quality}")

    if video_url:
        file_path = download_video(video_url, quality)
        if file_path and "Error:" not in file_path:  # Check for error message
            return send_file(file_path, as_attachment=True)
        else:
            return file_path, 500  # Return the error message
    else:
        return render_template("index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)  # Enable debug mode during development
