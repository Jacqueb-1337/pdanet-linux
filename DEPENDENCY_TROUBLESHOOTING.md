# PdaNet Linux - Dependency Troubleshooting Guide

This guide helps you resolve common dependency issues when installing or running PdaNet Linux.

## Quick Diagnosis

Run the dependency checker to see what's missing:

```bash
cd ~/pdanet-linux
python3 check_dependencies.py
```

This will show you exactly which dependencies are missing and provide instructions on how to fix them.

## Common Issues and Solutions

### Issue 1: ModuleNotFoundError: No module named 'gi.repository'

**Cause:** Python GTK bindings (PyGObject) are not properly installed.

**Solution:**

```bash
# Install all required GTK dependencies
sudo apt-get update
sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 \
  gir1.2-glib-2.0 python3-cairo libgirepository1.0-dev

# Verify the fix
python3 -c "import gi; print('GTK bindings OK')"
```

### Issue 2: System tray icon not appearing

**Cause:** AppIndicator library is missing or using wrong variant for your distribution.

**Solution for Ubuntu/Linux Mint:**
```bash
sudo apt-get install -y gir1.2-appindicator3-0.1
```

**Solution for Debian:**
```bash
sudo apt-get install -y gir1.2-ayatanaappindicator3-0.1
```

**Note:** The application will still work without system tray support, but you won't have a tray icon.

### Issue 3: Desktop notifications not working

**Cause:** libnotify bindings are missing.

**Solution:**
```bash
sudo apt-get install -y gir1.2-notify-0.7
```

### Issue 4: Cannot import Gtk

**Full error:** `ValueError: Namespace Gtk not available`

**Solution:**
```bash
# Make sure GTK typelib is installed
sudo apt-get install -y gir1.2-gtk-3.0

# Verify
python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; print('GTK OK')"
```

### Issue 5: GUI won't launch after installation

**Solution - Complete reinstallation:**

```bash
cd ~/pdanet-linux

# Remove old installation
sudo ./uninstall.sh

# Clean reinstall
sudo ./install.sh

# Verify dependencies
python3 check_dependencies.py
```

## Distribution-Specific Notes

### Ubuntu / Linux Mint
- Use `gir1.2-appindicator3-0.1` for system tray
- All dependencies should be available in default repositories

### Debian
- Use `gir1.2-ayatanaappindicator3-0.1` for system tray (replaces deprecated AppIndicator)
- You may need to enable additional repositories for some packages

### Other Debian-based Distributions
- Try Ubuntu packages first, fall back to Debian equivalents if needed
- The installer script now handles both variants automatically

## Complete Dependency List

### Required (Critical)
These must be installed for the application to run:

```bash
sudo apt-get install -y \
  python3-gi \
  python3-gi-cairo \
  gir1.2-gtk-3.0 \
  gir1.2-glib-2.0 \
  python3-cairo \
  libgirepository1.0-dev \
  redsocks \
  iptables \
  iptables-persistent \
  curl \
  net-tools
```

### Optional (Enhanced Features)
These enhance functionality but aren't strictly required:

```bash
# System tray support (choose one based on your distribution)
sudo apt-get install -y gir1.2-appindicator3-0.1  # Ubuntu/Mint
# OR
sudo apt-get install -y gir1.2-ayatanaappindicator3-0.1  # Debian

# Desktop notifications
sudo apt-get install -y gir1.2-notify-0.7
```

## Verification Steps

After installing dependencies, verify everything is working:

1. **Check Python GTK bindings:**
   ```bash
   python3 -c "import gi; from gi.repository import Gtk, GLib, Gdk; print('GTK bindings: OK')"
   ```

2. **Check AppIndicator (if installed):**
   ```bash
   python3 -c "import gi; gi.require_version('AppIndicator3', '0.1'); from gi.repository import AppIndicator3; print('AppIndicator: OK')" 2>/dev/null || \
   python3 -c "import gi; gi.require_version('AyatanaAppIndicator3', '0.1'); from gi.repository import AyatanaAppIndicator3; print('AyatanaAppIndicator: OK')"
   ```

3. **Run full dependency check:**
   ```bash
   python3 check_dependencies.py
   ```

4. **Launch GUI:**
   ```bash
   pdanet-gui-v2
   ```

## Getting Help

If you're still having issues after following this guide:

1. Run the dependency checker and save the output:
   ```bash
   python3 check_dependencies.py > dependency_check.txt 2>&1
   ```

2. Check the application logs:
   ```bash
   cat ~/.config/pdanet-linux/pdanet.log
   ```

3. Open an issue on GitHub with:
   - Your Linux distribution and version (`cat /etc/os-release`)
   - Output from dependency checker
   - Any error messages from the application
   - Contents of the log file

## Quick Reference

| Problem | Quick Fix |
|---------|-----------|
| "No module named 'gi'" | `sudo apt install python3-gi python3-gi-cairo` |
| "Namespace Gtk not available" | `sudo apt install gir1.2-gtk-3.0` |
| No system tray icon | `sudo apt install gir1.2-appindicator3-0.1` (Ubuntu) or `gir1.2-ayatanaappindicator3-0.1` (Debian) |
| No notifications | `sudo apt install gir1.2-notify-0.7` |
| GUI won't launch | Run `python3 check_dependencies.py` for diagnosis |

---

**Last Updated:** 2026-01-24
**Version:** 2.2.1
