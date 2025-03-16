from flask import Flask, render_template, request, send_file, session, redirect, url_for, jsonify
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
app.secret_key = "your_secret_key"  # Required for session management

# Load Instagram Credentials Securely
load_dotenv()
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

DOWNLOADS_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)  # Ensure download folder exists

# ======= INSTAGRAM DOWNLOAD (PLAYWRIGHT) =======
def download_instagram_post_playwright(post_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        })
        page.goto(post_url, timeout=60000)
        time.sleep(random.randint(5, 10))
        media_url = page.locator("video").get_attribute("src")
        if not media_url:
            image_element = page.wait_for_selector("article img", timeout=10000)
            if image_element:
                media_url = image_element.get_attribute("src")
        browser.close()
        if not media_url:
            return None
        parsed_url = urlparse(media_url)
        filename = os.path.basename(parsed_url.path)
        filepath = os.path.join(DOWNLOADS_FOLDER, filename)
        with open(filepath, "wb") as file:
            file.write(requests.get(media_url).content)
        return filepath

# ======= FLASK ROUTES =======
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/set_cookie_permission", methods=["POST"])
def set_cookie_permission():
    session["cookies_accepted"] = request.json.get("accept", False)
    return jsonify({"status": "success"})

@app.route("/instagram", methods=["GET", "POST"])
def instagram_downloader():
    if session.get("cookies_accepted"):
        if request.method == "POST":
            post_url = request.form["url"]
            filepath = download_instagram_post_playwright(post_url)
            if filepath:
                return send_file(filepath, as_attachment=True)
            return "Error: Instagram post could not be downloaded.", 500
    return redirect(url_for("index"))
    return render_template("instagram_downloader.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    if email:
        session["user_email"] = email
        return redirect(url_for("index"))
    return "Email is required.", 400

@app.route("/video", methods=["POST"])
def video_downloader():
    if "user_email" in session:
        video_url = request.form.get("video_url")
        if video_url:
            unique_filename = f"video_{uuid.uuid4().hex}.mp4"
            video_path = os.path.join(DOWNLOADS_FOLDER, unique_filename)
            ydl_opts = {"format": "best", "outtmpl": video_path}
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
                return send_file(video_path, as_attachment=True)
            except:
                return "Error: Video could not be downloaded.", 500
    return "Login required.", 403
    return render_template("index.html")
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
