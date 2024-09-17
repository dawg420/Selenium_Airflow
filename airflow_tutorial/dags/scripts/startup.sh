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
export DISPLAY=:0
export HOME=/root  # or /home/yourusername if you're using a non-root user

# Remove any old Xvfb lock file
rm -f /tmp/.X0-lock

# Create the .fluxbox directory
mkdir -p $HOME/.fluxbox

# Create the init file with desired parameters
cat > $HOME/.fluxbox/init <<EOF
session.ignoreBorder:               false
session.forcePseudoTransparency:    false
session.colorsPerChannel:           4
session.doubleClickInterval:        250
session.tabPadding:                 0
session.styleOverlay:               \$HOME/.fluxbox/overlay
session.slitlistFile:               \$HOME/.fluxbox/slitlist
session.appsFile:                   \$HOME/.fluxbox/apps
session.tabsAttachArea:             Window
session.menuSearch:                 true
session.cacheLife:                  5
session.cacheMax:                   200
session.autoRaiseDelay:             250
session.screen0.opaqueMove:         true
session.screen0.fullMaximization:   false
session.screen0.maxIgnoreIncrement: false
session.screen0.maxDisableMove:     false
session.screen0.maxDisableResize:   false
session.screen0.workspacewarping:   true
session.screen0.showwindowposition: true
session.screen0.autoRaise:          false
session.screen0.clickRaises:        true
session.screen0.defaultDeco:        NORMAL
session.screen0.tab.placement:      Top
session.screen0.windowMenu:         \$HOME/.fluxbox/windowmenu
session.screen0.noFocusWhileTypingDelay: 0
session.screen0.workspaces:         4
session.screen0.edgeSnapThreshold:  0
session.screen0.window.focus.alpha: 255
session.screen0.window.unfocus.alpha: 255
session.screen0.menu.alpha:         255
session.screen0.menuDelay:          0
session.screen0.tab.width:          64
session.screen0.tooltipDelay:       500
session.screen0.allowRemoteActions: true
session.screen0.clientMenu.usePixmap: true
session.screen0.tabs.usePixmap:     false
session.screen0.tabs.maxOver:       false
session.screen0.tabs.intitlebar:    true
session.screen0.focusModel:         ClickFocus
session.screen0.tabFocusModel:      ClickToTabFocus
session.screen0.focusNewWindows:    true
session.screen0.focusSameHead:      true
session.screen0.rowPlacementDirection: LeftToRight
session.screen0.colPlacementDirection: TopToBottom
session.screen0.windowPlacement:    RowSmartPlacement
EOF

# Start Xvfb on display :0
Xvfb :0 -screen 0 1280x720x16 &

# Wait for Xvfb to start
sleep 2

# Start Fluxbox window manager
fluxbox -display :0 &

# Wait for Fluxbox to start
sleep 2

# Start x11vnc
x11vnc -display :0 -forever -usepw &

# Add delay to allow services to start
sleep 5

# Run python script
python channel_news_asia.py
