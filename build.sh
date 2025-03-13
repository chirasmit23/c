#!/bin/bash

# Install Google Chrome on Linux
if ! command -v google-chrome &> /dev/null; then
  echo "Installing Google Chrome..."
  wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
  echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list
  sudo apt update
  sudo apt install -y google-chrome-stable
fi
