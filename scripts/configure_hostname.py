#!/usr/bin/env python3
"""Install dynamic identity system for hardware-based device naming"""
import os
import sys
import stat
from pathlib import Path
from config import HOSTNAME_PREFIX, ROOTFS_MOUNT

# Identity generation script (runs on Pi at first boot)
IDENTITY_SCRIPT = """#!/bin/bash
# Generate unique device identity with satellite name
# Runs once on first boot to set hostname and WiFi AP name

set -e

MARKER_FILE="/var/lib/citrascope-identity-set"
NAME_FILE="/etc/citrascope-name"
PREFIX_FILE="/etc/citrascope-prefix"

# Exit if already run
if [ -f "$MARKER_FILE" ]; then
    exit 0
fi

# List of satellite/spacecraft names (easy to spell and recognize)
SATELLITES=(
    "voyager" "hubble" "galileo" "juno" "kepler"
    "pioneer" "viking" "luna" "apollo" "gemini"
    "mercury" "atlas" "titan" "orion" "phoenix"
    "spirit" "curiosity"
)

# Pick random satellite name
SATELLITE="${SATELLITES[$RANDOM % ${#SATELLITES[@]}]}"

# Read prefix from config (set at build time)
PREFIX=""
if [ -f "$PREFIX_FILE" ]; then
    PREFIX=$(cat "$PREFIX_FILE")
fi

# Generate device name: prefix-satellite
if [ -n "$PREFIX" ]; then
    DEVICE_NAME="${PREFIX}-${SATELLITE}"
else
    DEVICE_NAME="${SATELLITE}"
fi

echo "Generating device identity: $DEVICE_NAME"

# Update /etc/hostname
echo "$DEVICE_NAME" > /etc/hostname

# Update /etc/hosts
sed -i "s/^127\\.0\\.1\\.1.*/127.0.1.1\\t${DEVICE_NAME}/" /etc/hosts

# Update Comitup AP name
if [ -f /etc/comitup.conf ]; then
    sed -i "s/^ap_name:.*/ap_name: ${DEVICE_NAME}/" /etc/comitup.conf
fi

# Save generated name for reference
echo "$DEVICE_NAME" > "$NAME_FILE"

# Set hostname immediately (log if it fails)
if ! hostnamectl set-hostname "$DEVICE_NAME" 2>&1; then
    echo "hostnamectl failed (dbus not ready?), hostname set via files" | logger -t citrascope-identity
fi

# Create marker file so we don't run again
mkdir -p "$(dirname "$MARKER_FILE")"
echo "$(date)" > "$MARKER_FILE"

echo "Device identity set to: $DEVICE_NAME"
"""

# Systemd service file
IDENTITY_SERVICE = """[Unit]
Description=Generate CitraScope device identity
Documentation=https://github.com/citra-space/lemon-pi
DefaultDependencies=no
After=local-fs.target dbus.service
Before=avahi-daemon.service NetworkManager.service comitup.service
Requires=dbus.service
ConditionPathExists=!/var/lib/citrascope-identity-set

[Service]
Type=oneshot
ExecStart=/usr/local/bin/generate-citrascope-identity
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""

def install_identity_system():
    """Install identity generation script and service"""
    from config import ROOTFS_MOUNT, BOOT_MOUNT
    
    print("Installing dynamic identity system...")
    
    # Set initial hostname to "citrascope" (will be updated on first boot)
    hostname_file = Path(ROOTFS_MOUNT) / 'etc/hostname'
    hostname_file.write_text("citrascope\n")
    print(f"  ✓ Set initial hostname to 'citrascope'")
    
    # Update /etc/hosts
    hosts_file = Path(ROOTFS_MOUNT) / 'etc/hosts'
    if hosts_file.exists():
        content = hosts_file.read_text()
        # Replace 127.0.1.1 line
        import re
        content = re.sub(r'^127\.0\.1\.1.*$', '127.0.1.1\tcitrascope', content, flags=re.MULTILINE)
        hosts_file.write_text(content)
    print(f"  ✓ Updated /etc/hosts")
    
    # Write prefix to config file on Pi
    prefix_file = Path(ROOTFS_MOUNT) / 'etc/citrascope-prefix'
    prefix_file.write_text(HOSTNAME_PREFIX)
    print(f"  ✓ Set hostname prefix: '{HOSTNAME_PREFIX}'")
    
    # Write identity generation script
    script_dst = Path(ROOTFS_MOUNT) / 'usr/local/bin/generate-citrascope-identity'
    script_dst.parent.mkdir(parents=True, exist_ok=True)
    script_dst.write_text(IDENTITY_SCRIPT)
    
    # Make executable
    script_dst.chmod(script_dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  ✓ Installed identity script to /usr/local/bin/")
    
    # Write systemd service
    service_dst = Path(ROOTFS_MOUNT) / 'etc/systemd/system/citrascope-identity.service'
    service_dst.parent.mkdir(parents=True, exist_ok=True)
    service_dst.write_text(IDENTITY_SERVICE)
    print(f"  ✓ Installed systemd service")
    
    # Enable service
    wants_dir = Path(ROOTFS_MOUNT) / 'etc/systemd/system/multi-user.target.wants'
    wants_dir.mkdir(parents=True, exist_ok=True)
    
    service_link = wants_dir / 'citrascope-identity.service'
    if service_link.exists() or service_link.is_symlink():
        service_link.unlink()
    
    service_link.symlink_to('/etc/systemd/system/citrascope-identity.service')
    print(f"  ✓ Enabled citrascope-identity.service")
    
    return True

def main():
    """Main entry point - installs identity system"""
    try:
        install_identity_system()
        return True
    except Exception as e:
        print(f"Error installing identity system: {e}")
        return False

if __name__ == "__main__":
    main()
