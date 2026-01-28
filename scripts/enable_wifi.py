#!/usr/bin/env python3
"""
Enable WiFi hardware (unblock RF-kill)
Required for WiFi to work on Raspberry Pi when no regulatory domain set at boot.
Based on: https://gist.github.com/davesteele/9b5f566ad976b083b3c278e0e1fdfcfe
"""

import os
import sys
from pathlib import Path
from config import ROOTFS_MOUNT

def main():
    """Enable WiFi by creating systemd service to turn on radio"""
    if not os.path.exists(ROOTFS_MOUNT):
        print(f"Error: Root filesystem path {ROOTFS_MOUNT} does not exist")
        return False
    
    print("Enabling WiFi hardware...")
    
    # Create systemd service to enable WiFi radio on boot
    service_content = '''[Unit]
Description=Turn wifi on, regardless of regulatory domain
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/nmcli radio wifi on

[Install]
WantedBy=NetworkManager.service
'''
    
    # Write service file
    service_path = Path(ROOTFS_MOUNT) / 'etc/systemd/system/wifi-on.service'
    with open(service_path, 'w') as f:
        f.write(service_content)
    
    # Enable service
    service_link = Path(ROOTFS_MOUNT) / 'etc/systemd/system/NetworkManager.service.wants/wifi-on.service'
    service_link.parent.mkdir(parents=True, exist_ok=True)
    
    if service_link.exists() or service_link.is_symlink():
        service_link.unlink()
    
    service_link.symlink_to('/etc/systemd/system/wifi-on.service')
    
    print("  ✓ Created wifi-on.service")
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
