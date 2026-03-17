"""
Lemon Pi Configuration
Centralized configuration for all build scripts.
Edit these values to customize your build.
"""

import os
import re
import sys

def validate_safe_string(value, field_name):
    """
    Validate that a string doesn't contain shell metacharacters.
    Prevents command injection via config values.
    """
    # Allow alphanumeric, underscore, hyphen, dot, forward slash, colon (for URLs)
    if not re.match(r'^[a-zA-Z0-9_./:@-]+$', value):
        print(f"ERROR: {field_name} contains invalid characters: {value}", file=sys.stderr)
        print(f"Only alphanumeric, underscore, hyphen, dot, forward slash, colon, and @ are allowed.", file=sys.stderr)
        sys.exit(1)

# System User Configuration
USERNAME = "citra"
PASSWORD = "citra"
USER_UID = 1001
USER_GID = 1001

# Hostname and Network
HOSTNAME_PREFIX = "citrascope"  # Prefix for dynamic hostname: {prefix}-{model}-{serial}
MDNS_DOMAIN = f"{HOSTNAME_PREFIX}.local"

# WiFi Access Point Configuration
WIFI_AP_PASSWORD = "citra"
WIFI_AP_SSID_PREFIX = HOSTNAME_PREFIX  # Will be: citrascope-{model}-{serial}

# Citrascope Configuration
CITRASCOPE_WEB_PORT = 80
CITRASCOPE_VENV_PATH = "/home/{}/".format(USERNAME) + ".citrascope_venv"
CITRASCOPE_SOURCE_DIR = "/home/{}/citrascope".format(USERNAME)
CITRASCOPE_GITHUB_REPO = os.environ.get("CITRASCOPE_GITHUB_REPO", "https://github.com/citra-space/citrascope.git")
CITRASCOPE_GITHUB_REF = os.environ.get("CITRASCOPE_GITHUB_REF", "main")

# Localization Settings
LOCALE = "en_US.UTF-8"
TIMEZONE = "America/Denver"
KEYBOARD_LAYOUT = "us"
WIFI_COUNTRY = "US"  # Required for WiFi to work (regulatory compliance)

# Mount Points
ROOTFS_MOUNT = "/mnt/part2"
BOOT_MOUNT = "/mnt/part1"

# System Packages to Install
SYSTEM_PACKAGES = [
    'python3-pip',
    'python3-venv',
    'cmake',
    'build-essential',
    'avahi-daemon',
    'avahi-utils',
    'indi-bin',  # INDI server for telescope/camera control
    'comitup',  # WiFi provisioning with captive portal
    'curl',
    'git',
    # Build dependencies for pyenv to compile Python 3.12
    'libssl-dev',
    'zlib1g-dev',
    'libbz2-dev',
    'libreadline-dev',
    'libsqlite3-dev',
    'libncurses5-dev',
    'libncursesw5-dev',
    'libffi-dev',
    'liblzma-dev',
    'tk-dev',
    'xz-utils',
    # Build dependencies for Python packages
    'libdbus-1-dev',  # Needed for dbus-python
    'libglib2.0-dev',  # Needed for dbus-gmain
    'libjpeg-dev',  # Needed for Pillow
    'zlib1g-dev',  # Already listed above but also needed for Pillow
    'liblcms2-dev',  # Needed for Pillow color management
    'libwebp-dev',  # Needed for Pillow WebP support
    'libharfbuzz-dev',  # Needed for Pillow text rendering
    'libfribidi-dev',  # Needed for Pillow bidirectional text
    'libxcb1-dev',  # Needed for Pillow X11 support
    # GPS Time Synchronization
    'chrony',  # Modern NTP daemon with GPS support
    'gpsd',  # GPS daemon for hardware abstraction
    'gpsd-clients',  # GPS testing tools (cgps, gpsmon)
    'pps-tools',  # PPS debugging utilities (ppstest)
]

# User Groups (in addition to primary group)
USER_GROUPS = [
    'sudo',      # Admin/package installation
    'video',     # Camera access
    'plugdev',   # USB devices (cameras, mounts)
    'dialout',   # Serial ports (ttyACM*, ttyUSB*)
    'netdev',    # Network management (WiFi AP)
    'gpio',      # GPIO hardware access
    'i2c',       # I2C bus devices
    'spi',       # SPI bus devices
]

# GPS Timing Configuration
GPS_PPS_GPIO = 18  # GPIO pin for PPS signal (common convention)
GPS_ENABLE_PRIMARY_UART = True  # Enable /dev/ttyAMA0 on GPIO 14/15 (all Pi models)

# Hardware Driver Configuration
DRIVER_LIB_DIR = "/usr/local/lib"
UDEV_RULES_DIR = "/etc/udev/rules.d"

UDEV_RULE_TEMPLATE = 'SUBSYSTEM=="usb", ATTR{{idVendor}}=="{vendor}", MODE="0666", GROUP="plugdev"'

HARDWARE_DRIVERS = {
    "moravian": {
        "url": "https://www.gxccd.com/download?id=472&lang=409",
        "lib_name": "libgxccd.so",
        "usb_vendor_id": "1347",
        "udev_rule_file": "99-moravian.rules",
    },
    "zwo_eaf": {
        "url": "https://dl.zwoastro.com/software?app=DeveloperEafSdk&platform=windows86&region=Overseas",
        "lib_name": "libEAFFocuser.so",
        "usb_vendor_id": "03c3",
        "udev_rule_file": "99-zwo.rules",
    },
}

# Validate configuration to prevent shell injection
validate_safe_string(USERNAME, "USERNAME")
validate_safe_string(HOSTNAME_PREFIX, "HOSTNAME_PREFIX")
validate_safe_string(WIFI_AP_PASSWORD, "WIFI_AP_PASSWORD")
validate_safe_string(WIFI_AP_SSID_PREFIX, "WIFI_AP_SSID_PREFIX")
validate_safe_string(CITRASCOPE_VENV_PATH, "CITRASCOPE_VENV_PATH")
validate_safe_string(CITRASCOPE_SOURCE_DIR, "CITRASCOPE_SOURCE_DIR")
validate_safe_string(CITRASCOPE_GITHUB_REPO, "CITRASCOPE_GITHUB_REPO")
validate_safe_string(CITRASCOPE_GITHUB_REF, "CITRASCOPE_GITHUB_REF")
