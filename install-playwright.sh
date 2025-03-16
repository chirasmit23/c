#!/bin/bash
set -e  # Exit if any command fails

echo "Updating package lists..."
apt-get update -y

echo "Installing system dependencies..."
apt-get install -y wget curl unzip libnss3 libxss1 libasound2 \
libatk1.0-0 libatk-bridge2.0-0 libgtk-3-0 libgraphene-1.0-0 \
libgstgl-1.0-0 libgstcodecparsers-1.0-0 libavif15 libenchant-2-2 \
libsecret-1-0 libmanette-0.2-0 libgles2-mesa

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install playwright
playwright install

echo "Installing Playwright with dependencies..."
npx playwright install --with-deps chromium  # This is enough!

echo "Setup complete!"
