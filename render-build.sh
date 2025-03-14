#!/bin/bash
set -e  # Exit if any command fails

echo "Updating package lists..."
apt-get update -y

echo "Installing system dependencies..."
apt-get install -y wget curl unzip libnss3 libxss1 libasound2 \
libatk1.0-0 libatk-bridge2.0-0 libgtk-3-0 libgtk-4-1 libgraphene-1.0-0 \
libgstgl-1.0-0 libgstcodecparsers-1.0-0 libavif15 libenchant-2-2 \
libsecret-1-0 libmanette-0.2-0 libgles2-mesa libgstreamer1.0-0 \
libgstreamer-plugins-base1.0-0 libxrandr2 libgbm1 libpangocairo-1.0-0 \
libpangoft2-1.0-0 libcups2 libxcomposite1 libxdamage1 libxext6 \
libxfixes3 libxrender1 libxi6 libxcursor1 libwayland-egl1 \
libwayland-server0 libwayland-client0 libatk1.0-0 libgdk-pixbuf2.0-0 \
libevent-2.1-7 libgles2 libegl1 libegl-mesa0

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Installing Playwright with dependencies..."
npx playwright install --with-deps chromium  # This is enough!

echo "Setup complete!"
