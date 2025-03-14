from flask import Flask, render_template, request, jsonify
import yt_dlp
import os
import random
import requests
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

# Initialize Flask App
app = Flask(__name__, template_folder="templates")

# Proxy Configuration (Optional)
PROXY = "60.183.57.76"
PROXIES = {"http": f"http://{PROXY}", "https": f"http://{PROXY}"}

# ======= INSTAGRAM DOWNLOAD (PLAYWRIGHT) =======
def get_instagram_media_url(post_url):
    """Uses Playwright to extract the direct Instagram video/image URL."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })

        page.goto(post_url, timeout=60000)
        media_url = None
        try:
            media_url = page.locator("video").get_attribute("src")
            if not media_url:
                media_url = page.locator("img").get_attribute("src")
        except Exception as e:
            print(f"Error extracting media URL: {e}")
        
        browser.close()
        return media_url

# ======= YOUTUBE & INSTAGRAM REELS DOWNLOAD (yt-dlp) =======
def get_video_url(post_url):
    """Extracts the direct video URL using yt-dlp without downloading."""
    ydl_opts = {
        "quiet": True,
        "proxy": f"http://{PROXY}",
        "format": "best",
        "simulate": True,
        "get_url": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(post_url, download=False)
            return result.get("url")
    except Exception as e:
        print(f"Error fetching video URL: {e}")
        return None

# ======= FLASK ROUTES =======
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/instagram", methods=["POST"])
def instagram_downloader():
    post_url = request.form.get("url")
    media_url = get_instagram_media_url(post_url)
    return jsonify({"media_url": media_url}) if media_url else jsonify({"error": "Could not extract media URL"}), 500

@app.route("/video", methods=["POST"])
def video_downloader():
    video_url = request.form.get("video_url")
    direct_url = get_video_url(video_url)
    return jsonify({"direct_url": direct_url}) if direct_url else jsonify({"error": "Could not fetch video URL"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
