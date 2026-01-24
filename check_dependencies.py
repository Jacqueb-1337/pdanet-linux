#!/usr/bin/env python3
"""
PdaNet Linux - Dependency Validation Script
Checks if all required dependencies are properly installed
"""

import sys
import subprocess
from typing import Tuple, List

# Color codes for terminal output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;36m'
NC = '\033[0m'  # No Color


def check_python_version() -> Tuple[bool, str]:
    """Check if Python version is 3.8 or higher"""
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 8:
        return True, f"Python {major}.{minor}"
    return False, f"Python {major}.{minor} (need 3.8+)"


def check_python_package(package_name: str, import_name: str = None) -> Tuple[bool, str]:
    """Check if a Python package can be imported"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        return True, "Installed"
    except ImportError as e:
        return False, f"Missing: {str(e)}"


def check_gi_module(module_name: str, version: str = None) -> Tuple[bool, str]:
    """Check if a GI module is available"""
    try:
        import gi
        if version:
            gi.require_version(module_name, version)
        from gi.repository import GObject
        # Try to get the module
        module = getattr(__import__('gi.repository', fromlist=[module_name]), module_name)
        return True, "Available"
    except (ImportError, ValueError, AttributeError) as e:
        return False, f"Missing: {str(e)}"


def check_system_package(package_name: str) -> Tuple[bool, str]:
    """Check if a system package is installed (dpkg)"""
    try:
        result = subprocess.run(
            ['dpkg', '-l', package_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and 'ii' in result.stdout:
            return True, "Installed"
        return False, "Not installed"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "Cannot check (dpkg not available)"


def check_command(command: str) -> Tuple[bool, str]:
    """Check if a command is available in PATH"""
    try:
        result = subprocess.run(
            ['which', command],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, "Not found in PATH"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "Cannot check"


def print_result(check_name: str, success: bool, message: str, critical: bool = True):
    """Print formatted check result"""
    status_symbol = f"{GREEN}✓{NC}" if success else f"{RED}✗{NC}"
    criticality = "" if not critical else ""
    
    if success:
        print(f"{status_symbol} {check_name}: {GREEN}{message}{NC}")
    else:
        severity = RED if critical else YELLOW
        print(f"{status_symbol} {check_name}: {severity}{message}{NC}")


def main():
    """Run all dependency checks"""
    print(f"{BLUE}╔════════════════════════════════════════╗{NC}")
    print(f"{BLUE}║  PdaNet Linux - Dependency Check      ║{NC}")
    print(f"{BLUE}╚════════════════════════════════════════╝{NC}")
    print()
    
    all_critical_ok = True
    all_optional_ok = True
    
    # Python version
    print(f"{BLUE}[1] Python Environment{NC}")
    success, msg = check_python_version()
    print_result("Python Version", success, msg, critical=True)
    if not success:
        all_critical_ok = False
    print()
    
    # Core Python packages
    print(f"{BLUE}[2] Python GTK Bindings{NC}")
    
    checks = [
        ("gi (PyGObject)", "gi", True),
        ("gi.repository.Gtk", "gi.repository.Gtk", True),
        ("gi.repository.GLib", "gi.repository.GLib", True),
        ("gi.repository.Gdk", "gi.repository.Gdk", True),
    ]
    
    for name, import_name, critical in checks:
        success, msg = check_python_package(name, import_name)
        print_result(name, success, msg, critical=critical)
        if not success and critical:
            all_critical_ok = False
    print()
    
    # GI modules
    print(f"{BLUE}[3] GTK GObject Introspection Modules{NC}")
    
    # Check for AppIndicator (try both variants)
    appindicator_found = False
    for variant in ["AppIndicator3", "AyatanaAppIndicator3"]:
        success, msg = check_gi_module(variant, "0.1")
        if success:
            print_result(f"System Tray ({variant})", True, msg, critical=False)
            appindicator_found = True
            break
    
    if not appindicator_found:
        print_result("System Tray (AppIndicator3/AyatanaAppIndicator3)", False, 
                    "Neither Ubuntu nor Debian variant found", critical=False)
        all_optional_ok = False
    
    success, msg = check_gi_module("Notify", "0.7")
    print_result("Desktop Notifications (Notify)", success, msg, critical=False)
    if not success:
        all_optional_ok = False
    print()
    
    # System packages
    print(f"{BLUE}[4] System Packages{NC}")
    
    sys_packages = [
        ("python3-gi", True),
        ("python3-gi-cairo", True),
        ("gir1.2-gtk-3.0", True),
        ("gir1.2-glib-2.0", True),
        ("python3-cairo", True),
        ("libgirepository1.0-dev", False),
        ("gir1.2-notify-0.7", False),
    ]
    
    for pkg, critical in sys_packages:
        success, msg = check_system_package(pkg)
        print_result(pkg, success, msg, critical=critical)
        if not success and critical:
            all_critical_ok = False
        elif not success and not critical:
            all_optional_ok = False
    
    # Check for AppIndicator system packages
    appindicator_pkg_found = False
    for pkg in ["gir1.2-appindicator3-0.1", "gir1.2-ayatanaappindicator3-0.1"]:
        success, msg = check_system_package(pkg)
        if success:
            print_result(f"System Tray Package ({pkg})", True, msg, critical=False)
            appindicator_pkg_found = True
            break
    
    if not appindicator_pkg_found:
        print_result("System Tray Package", False, 
                    "Neither Ubuntu nor Debian variant found", critical=False)
        all_optional_ok = False
    print()
    
    # System commands
    print(f"{BLUE}[5] System Commands{NC}")
    
    commands = [
        ("redsocks", True),
        ("iptables", True),
        ("nmcli", True),
        ("curl", False),
    ]
    
    for cmd, critical in commands:
        success, msg = check_command(cmd)
        print_result(cmd, success, msg, critical=critical)
        if not success and critical:
            all_critical_ok = False
        elif not success and not critical:
            all_optional_ok = False
    print()
    
    # Summary
    print(f"{BLUE}╔════════════════════════════════════════╗{NC}")
    print(f"{BLUE}║            Summary                     ║{NC}")
    print(f"{BLUE}╚════════════════════════════════════════╝{NC}")
    
    if all_critical_ok:
        print(f"{GREEN}✓ All critical dependencies are satisfied!{NC}")
        if all_optional_ok:
            print(f"{GREEN}✓ All optional dependencies are satisfied!{NC}")
            print(f"\n{GREEN}You can now run: pdanet-gui-v2{NC}")
        else:
            print(f"{YELLOW}⚠ Some optional features may not work (system tray, notifications){NC}")
            print(f"{GREEN}But the core application should work fine!{NC}")
            print(f"\n{GREEN}You can run: pdanet-gui-v2{NC}")
    else:
        print(f"{RED}✗ Critical dependencies are missing!{NC}")
        print(f"\n{YELLOW}To fix, run the following commands:{NC}")
        print(f"\n{BLUE}# Install system dependencies{NC}")
        print(f"sudo apt-get update")
        print(f"sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 \\")
        print(f"  gir1.2-glib-2.0 python3-cairo gir1.2-notify-0.7 \\")
        print(f"  gir1.2-appindicator3-0.1 || \\")
        print(f"  sudo apt-get install -y gir1.2-ayatanaappindicator3-0.1")
        print(f"\n{BLUE}# Or re-run the installer{NC}")
        print(f"sudo ./install.sh")
    
    print()
    return 0 if all_critical_ok else 1


if __name__ == "__main__":
    sys.exit(main())
