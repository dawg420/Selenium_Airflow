#!/bin/sh

# Update and upgrade packages
apt-get update && apt-get upgrade -y

# Install dependencies
apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    unzip \
    gnupg \
    xvfb \
    x11vnc \
    fluxbox \
    xterm \
    libffi-dev \
    libssl-dev \
    zlib1g-dev \
    bzip2 \
    libreadline-dev \
    sqlite3 \
    git \
    libnss3 \
    libfreetype6 \
    libharfbuzz0b \
    ca-certificates \
    fonts-freefont-ttf \
    chromium \
    chromium-driver

# Install x11vnc
mkdir -p ~/.vnc
x11vnc -storepasswd 1234 ~/.vnc/passwd
export DISPLAY=:0

# Clean up unnecessary files after installation
apt-get clean
rm -rf /var/lib/apt/lists/*

# Remove temporary dependencies if any (replace with correct packages if needed)
# apt-get remove -y build-essential curl wget gnupg

# Remove any old Xvfb lock file
rm -f /tmp/.X0-lock

# Run Xvfb on display 0
Xvfb :0 -screen 0 1280x720x16 &

# Run fluxbox window manager on display 0
fluxbox -display :0 &

# Run x11vnc on display 0
x11vnc -display :0 -forever -usepw &

# Add delay to allow services to start
sleep 5

# Run python script
python test_nodriver.py
