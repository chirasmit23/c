#!/bin/bash
echo "Starting build process..."

# Update packages
apt-get update && apt-get install -y wget unzip

# Install Chromium (if needed)
apt-get install -y chromium-browser

# Install dependencies
pip install -r requirements.txt

echo "Build process complete!"
