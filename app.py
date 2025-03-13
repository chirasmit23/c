from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for
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

# Load Instagram Credentials Securely
load_dotenv()
USERNAME = os.getenv("INSTA_USERNAME")
PASSWORD = os.getenv("INSTA_PASSWORD")

DOWNLOADS_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)  # Ensure download folder exists

def restart_app():
    """Restart the app after a task completion"""
    time.sleep(2)  # Small delay before restarting
    os.execv(__file__, ["python"] + os.sys.argv)  # Restart the script

def download_instagram_post(post_url, username, password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://www.instagram.com/accounts/login/", timeout=60000)
        time.sleep(3)

        page.fill("input[name='username']", username)
        page.fill("input[name='password']", password)
        page.click("button[type='submit']")
        time.sleep(5)

        page.goto(post_url, timeout=60000)
        time.sleep(3)

        try:
            media_url = page.locator("article img").get_attribute("src")
        except:
            media_url = None

        if not media_url:
            return None

        filename = os.path.join(os.getcwd(), "downloaded_post.jpg")
        response = requests.get(media_url)
        with open(filename, "wb") as file:
            file.write(response.content)

        browser.close()
        return filename

@app.route("/download", methods=["POST"])
def download():
    data = request.json
    post_url = data.get("post_url")
    username = data.get("username")
    password = data.get("password")

    if not post_url or not username or not password:
        return jsonify({"error": "Missing parameters"}), 400

    filename = download_instagram_post(post_url, username, password)
    
    if filename:
        restart_app()  # Restart app after successful download
        return jsonify({"message": "Download successful", "file": filename})
    else:
        return jsonify({"error": "Download failed"}), 500

# Restart the app after each request
@app.before_request
def before_request():
    if request.endpoint in ["download"]:
        restart_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
