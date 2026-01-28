"""
Lemon Pi Configuration
Centralized configuration for all build scripts.
Edit these values to customize your build.
"""

# System User Configuration
USERNAME = "citra"
PASSWORD = "citra"
USER_UID = 1001
USER_GID = 1001

# Hostname and Network
HOSTNAME = "citrascope"
MDNS_DOMAIN = f"{HOSTNAME}.local"

# WiFi Access Point Configuration
WIFI_AP_PASSWORD = "citrascope"
WIFI_AP_SSID_PREFIX = HOSTNAME  # Will be: citrascope-{serial}
AP_NETWORK = "10.42.0.0/24"
AP_GATEWAY = "10.42.0.1"
AP_CHANNEL = 6

# Citrascope Configuration
CITRASCOPE_WEB_PORT = 24872
CITRASCOPE_VENV_PATH = "/home/{}/".format(USERNAME) + ".citrascope_venv"

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
