#!/usr/bin/env bash
echo "Installing Google Chrome..."
wget -qO- https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb > google-chrome.deb
apt update && apt install -y ./google-chrome.deb
rm google-chrome.deb
echo "Chrome installed successfully."
