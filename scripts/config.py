"""
Lemon Pi Configuration
Centralized configuration for all build scripts.
Edit these values to customize your build.
"""

import re
import sys

def validate_safe_string(value, field_name):
    """
    Validate that a string doesn't contain shell metacharacters.
    Prevents command injection via config values.
    """
    # Allow alphanumeric, underscore, hyphen, dot, forward slash
    if not re.match(r'^[a-zA-Z0-9_./-]+$', value):
        print(f"ERROR: {field_name} contains invalid characters: {value}", file=sys.stderr)
        print(f"Only alphanumeric, underscore, hyphen, dot, and forward slash are allowed.", file=sys.stderr)
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
CITRASCOPE_WEB_PORT = 24872
CITRASCOPE_VENV_PATH = "/home/{}/".format(USERNAME) + ".citrascope_venv"

# Localization Settings
LOCALE = "en_US.UTF-8"
TIMEZONE = "America/New_York"
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
]

# User Groups (in addition to primary group)
USER_GROUPS = [
    'sudo',      # Admin/package installation
    'video',     # Camera access
    'plugdev',   # USB devices (cameras, mounts)
    'netdev',    # Network management (WiFi AP)
    'gpio',      # GPIO hardware access
    'i2c',       # I2C bus devices
    'spi',       # SPI bus devices
]

# Validate configuration to prevent shell injection
validate_safe_string(USERNAME, "USERNAME")
validate_safe_string(HOSTNAME_PREFIX, "HOSTNAME_PREFIX")
validate_safe_string(WIFI_AP_PASSWORD, "WIFI_AP_PASSWORD")
validate_safe_string(WIFI_AP_SSID_PREFIX, "WIFI_AP_SSID_PREFIX")
validate_safe_string(CITRASCOPE_VENV_PATH, "CITRASCOPE_VENV_PATH")
