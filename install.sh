#!/bin/bash
#
# install.sh - Install PdaNet Linux Client
# Installs dependencies and configures system for PdaNet USB tethering
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Dynamically detect project directory (portable across systems)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_DIR="$SCRIPT_DIR"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║   PdaNet Linux Client - Installer     ║"
echo "║   USB Tethering for Linux Mint 22.x   ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Detect distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
    echo -e "Detected OS: ${GREEN}$PRETTY_NAME${NC}"
else
    echo -e "${RED}Error: Cannot detect OS${NC}"
    exit 1
fi

# Verify Linux Mint or Ubuntu
if [[ "$OS" != "linuxmint" ]] && [[ "$OS" != "ubuntu" ]]; then
    echo -e "${YELLOW}Warning: This installer is designed for Linux Mint/Ubuntu${NC}"
    echo -e "${YELLOW}Your OS: $OS - Installation may not work correctly${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

OFFLINE_MODE=false
for arg in "$@"; do
    if [[ "$arg" == "--offline" ]]; then
        OFFLINE_MODE=true
    fi
done

PACKAGES_FILE="$PROJECT_DIR/packaging/runtime-packages.txt"
if [[ ! -f "$PACKAGES_FILE" ]]; then
    echo -e "${RED}Error: Missing dependency list: $PACKAGES_FILE${NC}"
    exit 1
fi
mapfile -t CORE_PACKAGES < <(grep -Ev '^[[:space:]]*(#|$)' "$PACKAGES_FILE")

echo ""
if [[ "$OFFLINE_MODE" == true ]]; then
    echo -e "${YELLOW}[1/7]${NC} Offline mode: skipping package-list update"
else
    echo -e "${YELLOW}[1/7]${NC} Updating package lists..."
    apt-get update -qq
fi

echo -e "${YELLOW}[2/7]${NC} Checking dependencies..."
MISSING_PACKAGES=()
for pkg in "${CORE_PACKAGES[@]}"; do
    if [[ "$(dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null || true)" == "install ok installed" ]]; then
        echo "  ✓ $pkg already installed"
    elif [[ "$OFFLINE_MODE" == true ]]; then
        echo -e "  ${RED}✗${NC} $pkg is missing from the offline installation"
        MISSING_PACKAGES+=("$pkg")
    else
        echo "  Installing $pkg..."
        if ! DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$pkg" 2>/dev/null; then
            echo -e "  ${YELLOW}⚠${NC} Warning: Could not install $pkg"
            MISSING_PACKAGES+=("$pkg")
        fi
    fi
done

if [[ ${#MISSING_PACKAGES[@]} -gt 0 ]]; then
    echo -e "${RED}Error: Required packages are missing: ${MISSING_PACKAGES[*]}${NC}"
    exit 1
fi

# AppIndicator - try both old Ubuntu and new Debian packages
echo "  Checking system tray support..."
if [[ "$(dpkg-query -W -f='${Status}' gir1.2-appindicator3-0.1 2>/dev/null || true)" == "install ok installed" ]]; then
    echo "  ✓ gir1.2-appindicator3-0.1 already installed (Ubuntu)"
elif [[ "$(dpkg-query -W -f='${Status}' gir1.2-ayatanaappindicator3-0.1 2>/dev/null || true)" == "install ok installed" ]]; then
    echo "  ✓ gir1.2-ayatanaappindicator3-0.1 already installed (Debian)"
elif [[ "$OFFLINE_MODE" == true ]]; then
    echo -e "  ${YELLOW}⚠${NC} System tray package is not installed"
    echo "    GUI will work but the tray icon may not appear"
else
    if DEBIAN_FRONTEND=noninteractive apt-get install -y -qq gir1.2-appindicator3-0.1 2>/dev/null; then
        echo "  ✓ Installed gir1.2-appindicator3-0.1 (Ubuntu)"
    elif DEBIAN_FRONTEND=noninteractive apt-get install -y -qq gir1.2-ayatanaappindicator3-0.1 2>/dev/null; then
        echo "  ✓ Installed gir1.2-ayatanaappindicator3-0.1 (Debian)"
    else
        echo -e "  ${YELLOW}⚠${NC} Warning: Could not install system tray support"
        echo "    GUI will work but system tray icon may not appear"
    fi
fi

echo -e "${GREEN}✓${NC} Core dependencies ready"

echo -e "${YELLOW}[3/7]${NC} Configuring redsocks..."

# Backup existing redsocks config if it exists
if [ -f /etc/redsocks.conf ]; then
    cp /etc/redsocks.conf /etc/redsocks.conf.backup.$(date +%Y%m%d-%H%M%S)
    echo "  Existing config backed up"
fi

# Install our redsocks config
cp "$PROJECT_DIR/config/redsocks.conf" /etc/redsocks.conf
chown root:root /etc/redsocks.conf
chmod 644 /etc/redsocks.conf

echo -e "${GREEN}✓${NC} Redsocks configured"

echo -e "${YELLOW}[4/7]${NC} Configuring systemd service..."

# Make sure redsocks service is enabled but not started (we'll start it when connecting)
systemctl enable redsocks
systemctl stop redsocks 2>/dev/null || true

echo -e "${GREEN}✓${NC} Service configured"

echo -e "${YELLOW}[5/7]${NC} Setting up user permissions..."

# Allow current user to run connect/disconnect scripts without password
REAL_USER="${SUDO_USER:-$USER}"
if [ -z "$REAL_USER" ] || [ "$REAL_USER" = "root" ]; then
    echo -e "${RED}Error: Cannot determine non-root user${NC}"
    echo "Please run with: sudo -u <username> $0"
    exit 1
fi
SUDOERS_FILE="/etc/sudoers.d/pdanet-linux"

cat > "$SUDOERS_FILE" << EOF
# Allow user to run pdanet scripts without password
$REAL_USER ALL=(ALL) NOPASSWD: $PROJECT_DIR/pdanet-connect
$REAL_USER ALL=(ALL) NOPASSWD: $PROJECT_DIR/pdanet-disconnect
$REAL_USER ALL=(ALL) NOPASSWD: $PROJECT_DIR/pdanet-wifi-connect
$REAL_USER ALL=(ALL) NOPASSWD: $PROJECT_DIR/pdanet-wifi-disconnect
$REAL_USER ALL=(ALL) NOPASSWD: $PROJECT_DIR/pdanet-iphone-connect
$REAL_USER ALL=(ALL) NOPASSWD: $PROJECT_DIR/pdanet-iphone-disconnect
$REAL_USER ALL=(ALL) NOPASSWD: $PROJECT_DIR/scripts/stealth-mode.sh
$REAL_USER ALL=(ALL) NOPASSWD: $PROJECT_DIR/scripts/wifi-stealth.sh
$REAL_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active redsocks
$REAL_USER ALL=(ALL) NOPASSWD: /usr/sbin/iptables -t mangle -L PDANET_STEALTH
$REAL_USER ALL=(ALL) NOPASSWD: /usr/sbin/iptables -t mangle -L WIFI_STEALTH
EOF

chmod 440 "$SUDOERS_FILE"
echo -e "${GREEN}✓${NC} Sudo permissions configured for $REAL_USER"

echo -e "${YELLOW}[6/7]${NC} Creating convenience commands..."

# Create symlinks in /usr/local/bin for easy access
ln -sf "$PROJECT_DIR/pdanet-connect" /usr/local/bin/pdanet-connect
ln -sf "$PROJECT_DIR/pdanet-disconnect" /usr/local/bin/pdanet-disconnect
ln -sf "$PROJECT_DIR/pdanet-wifi-connect" /usr/local/bin/pdanet-wifi-connect
ln -sf "$PROJECT_DIR/pdanet-wifi-disconnect" /usr/local/bin/pdanet-wifi-disconnect
ln -sf "$PROJECT_DIR/pdanet-iphone-connect" /usr/local/bin/pdanet-iphone-connect
ln -sf "$PROJECT_DIR/pdanet-iphone-disconnect" /usr/local/bin/pdanet-iphone-disconnect
ln -sf "$PROJECT_DIR/scripts/stealth-mode.sh" /usr/local/bin/pdanet-stealth
ln -sf "$PROJECT_DIR/src/pdanet_gui_v2.py" /usr/local/bin/pdanet-gui-v2

# Make scripts executable
chmod +x "$PROJECT_DIR/src/pdanet_gui_v2.py"
chmod +x "$PROJECT_DIR/src/pdanet_usb_tunnel.py"
chmod +x "$PROJECT_DIR/pdanet-connect"
chmod +x "$PROJECT_DIR/pdanet-disconnect"
chmod +x "$PROJECT_DIR/pdanet-wifi-connect"
chmod +x "$PROJECT_DIR/pdanet-wifi-disconnect"
chmod +x "$PROJECT_DIR/pdanet-iphone-connect"
chmod +x "$PROJECT_DIR/pdanet-iphone-disconnect"

echo -e "${GREEN}✓${NC} Commands installed to /usr/local/bin"

echo -e "${YELLOW}[7/8]${NC} Installing GUI desktop launcher..."

# Install desktop file
cp "$PROJECT_DIR/config/pdanet-linux-v2.desktop" /usr/share/applications/pdanet-linux.desktop
chmod 644 /usr/share/applications/pdanet-linux.desktop

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

echo -e "${GREEN}✓${NC} GUI installed to application menu"

echo -e "${YELLOW}[8/9]${NC} Installing PolicyKit actions (pkexec)..."

# Install Polkit policy for pkexec prompts
POLKIT_DIR="/usr/share/polkit-1/actions"
install -m 0644 "$PROJECT_DIR/config/polkit/org.pdanetlinux.pkexec.policy" "$POLKIT_DIR/org.pdanetlinux.pkexec.policy"
echo -e "${GREEN}✓${NC} Polkit actions installed"

echo -e "${YELLOW}[9/9]${NC} Validating installation..."

# Run dependency check as the real user
if su - "$REAL_USER" -c "cd '$PROJECT_DIR' && python3 check_dependencies.py" > /tmp/pdanet_dep_check.log 2>&1; then
    echo -e "${GREEN}✓${NC} All dependencies validated successfully"
else
    echo -e "${YELLOW}⚠${NC} Some dependencies may be missing"
    echo "    Run 'python3 $PROJECT_DIR/check_dependencies.py' for details"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Installation Complete! ✓           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "1. Connect your Android device via USB"
echo "2. Open PdaNet+ app on Android"
echo "3. Enable 'Activate USB Mode' in PdaNet+"
echo ""
echo -e "${BLUE}Launch the GUI:${NC}"
echo "   ${GREEN}pdanet-gui-v2${NC}  (or search for 'PdaNet Linux' in your app menu)"
echo ""
echo -e "${BLUE}Connection Modes:${NC}"
echo "   ${GREEN}USB:${NC}     sudo pdanet-connect"
echo "   ${GREEN}WiFi:${NC}    sudo pdanet-wifi-connect"
echo "   ${GREEN}iPhone:${NC}  sudo pdanet-iphone-connect"
echo ""
echo -e "${BLUE}Optional - Enable stealth mode:${NC}"
echo "   ${GREEN}sudo pdanet-stealth enable${NC}"
echo "   (Hides tethering usage from carrier detection)"
echo ""
echo -e "${BLUE}To disconnect:${NC}"
echo "   ${GREEN}sudo pdanet-disconnect${NC} / ${GREEN}sudo pdanet-wifi-disconnect${NC} / ${GREEN}sudo pdanet-iphone-disconnect${NC}"
echo ""
echo -e "${YELLOW}Note:${NC} Make sure your Android device has PdaNet+ installed"
echo "Download from: https://pdanet.co/"
echo ""

exit 0
