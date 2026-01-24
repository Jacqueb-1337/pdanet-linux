# PdaNet Linux - Changelog

All notable changes to this project will be documented in this file.

## [2.2.1] - 2026-01-24

### 🔧 Bug Fixes & Compatibility

#### Fixed
- **Issue #2**: Fixed `ModuleNotFoundError: No module named 'gi.repository'` for users on Linux Mint 22
  - Improved GTK dependency installation in installer script
  - Added more comprehensive system package installation (python3-cairo, libgirepository1.0-dev, gir1.2-glib-2.0)
  - Better error handling for missing dependencies

- **Issue #1**: Added support for Debian's Ayatana AppIndicator (gir1.2-ayatanaappindicator3-0.1)
  - Application now automatically detects and uses either Ubuntu's AppIndicator3 or Debian's AyatanaAppIndicator3
  - Graceful fallback if neither is available (GUI works without system tray)
  - Fixes compatibility with pure Debian-based distributions

#### Added
- **Dependency Validation Tool** (`check_dependencies.py`)
  - Comprehensive dependency checker to help users troubleshoot installation issues
  - Validates Python version, GTK bindings, GI modules, system packages, and commands
  - Provides clear, actionable instructions for fixing missing dependencies
  - Color-coded output for easy identification of issues
  - Automatically run at end of installation

#### Improved
- **Documentation**: Added detailed troubleshooting section for GTK/dependency issues in README.md
- **Installation**: Installer now validates dependencies after installation
- **Manual Installation Instructions**: Updated with complete package list for both Ubuntu and Debian
- **System Requirements**: Added explicit listing of all required system packages

#### Technical Details
- Updated `install.sh` to install both core and optional GTK packages
- Modified `src/pdanet_gui_v2.py` to support both AppIndicator variants
- Modified `src/gui/main_window.py` with same AppIndicator fallback logic
- Installer now attempts Ubuntu packages first, then falls back to Debian equivalents

### Compatibility
- Tested on Linux Mint 22.2
- Compatible with both Ubuntu-based and Debian-based distributions
- Python 3.8+ required
- GTK 3.0+ with PyGObject required

---

## [2.2.0] - 2025-10-13

### 🔥 Major Feature Release

#### Added - NEW FEATURES
- **Connection History Viewer** (GUI Dialog)
  - View all past connection sessions with detailed stats
  - Shows timestamp, duration, data usage, interface, avg latency
  - Sort by any column, stores last 100 sessions
  - Clear history with confirmation dialog
  - Summary stats: total sessions, total data up/down, total time
  
- **Keyboard Shortcuts** 
  - Ctrl+C: Connect
  - Ctrl+D: Disconnect
  - Ctrl+H: View History
  - Ctrl+S: Open Settings
  - Ctrl+T: Run Speed Test
  - Ctrl+Q: Quit Application
  - F5: Refresh Display
  - Makes GUI incredibly fast to use!

- **Data Usage Warnings/Alerts System**
  - Configurable warning threshold (default: 1GB)
  - Configurable critical threshold (default: 5GB)
  - Desktop notifications when thresholds hit
  - Prevents spam (minimum 5 min between warnings)
  - Can be enabled/disabled in settings
  - Helps avoid carrier detection via excessive data usage

- **Network Quality Visual Indicator**
  - Real-time quality scoring (0-100%)
  - Color-coded status: EXCELLENT (green) → GOOD → FAIR (orange) → POOR → CRITICAL (red)
  - Based on latency, packet loss, and connection stability
  - Progressive penalty system with stability bonuses
  - Updates every second during active connection

- **Export/Import Settings**
  - Export all settings to JSON file (timestamped)
  - Import settings from JSON with validation
  - Automatic backup before import
  - Version tagging for compatibility
  - Accessible via Settings dialog

- **Quick-Switch Connection Profiles**
  - Dropdown menu for saved WiFi networks
  - One-click connection to saved profiles
  - Auto-loads saved passwords
  - Confirmation dialog before connecting
  - Refresh button to reload profile list

### Improved
- GUI layout optimized for all features
- Settings dialog now has Import/Export buttons
- Quality progress bar shows percentage and status
- Better error handling for all new features
- Enhanced notification system integration

### Technical
- All 105 unit tests still passing
- No regressions introduced
- Clean code architecture maintained
- Proper error handling throughout
- Memory efficient implementations

---

## [2.1.0] - 2025-10-13

### Added
- **Desktop Notifications**: Real-time notifications for connection state changes
- **Connection History Tracking**: Automatic session history logging  
- **Configurable Update Interval**: GUI update frequency now configurable (500-5000ms)

### Improved
- Code quality improvements
- Performance optimizations

### Fixed
- Minor linting issues
- Import handling for optional dependencies

---

## [2.0.0] - 2025-10-04

### Initial Release
- USB tethering support
- WiFi tethering with 6-layer carrier bypass
- iPhone Personal Hotspot support
- Professional cyberpunk GUI
- Auto-reconnect functionality
- Bandwidth monitoring
- Connection quality metrics
- System tray integration
- Configuration profiles
- Comprehensive test suite (105 tests)

---

## Features Summary (v2.2.0)

### Core Features
✅ USB Tethering  
✅ WiFi Hotspot Tethering (Primary Mode)  
✅ iPhone Personal Hotspot Support  
✅ 6-Layer Aggressive Carrier Bypass  
✅ Professional Cyberpunk GUI  

### New in v2.2.0
✅ **Connection History Viewer** (NEW)  
✅ **Keyboard Shortcuts** (NEW)  
✅ **Data Usage Warnings** (NEW)  
✅ **Network Quality Indicator** (NEW)  
✅ **Export/Import Settings** (NEW)  
✅ **Quick-Switch Profiles** (NEW)  

### Advanced Features
✅ Desktop Notifications  
✅ Auto-reconnect with exponential backoff  
✅ Real-time bandwidth monitoring  
✅ Connection quality metrics  
✅ System tray integration  
✅ Saved WiFi networks with passwords  
✅ Network scanning  
✅ Speed testing  

---

## Upgrade Instructions

### From 2.1.0 to 2.2.0

No breaking changes. Simply update and restart:

```bash
cd ~/pdanet-linux
git pull
pkill -f pdanet_gui_v2.py
pdanet-gui-v2
```

### New Keyboard Shortcuts

Press these keys anywhere in the GUI:
- **Ctrl+C**: Quick connect
- **Ctrl+D**: Quick disconnect
- **Ctrl+H**: View connection history
- **Ctrl+S**: Open settings
- **Ctrl+T**: Run speed test
- **Ctrl+Q**: Quit
- **F5**: Refresh display

### New Settings

Configure in Settings → Interface:
- Data usage warning threshold (MB)
- Data usage critical threshold (MB)
- Enable/disable warnings

---

## Known Issues

None! All 105 tests passing.

---

## Planned for v2.3.0
- Bandwidth usage graph visualization
- First-run setup wizard
- Multi-language support
- Theme variants
- VPN detection

---

**Version 2.2.0 Release Date**: October 13, 2025  
**Tested On**: Linux Mint 22.2, Ubuntu 24.04  
**License**: MIT
